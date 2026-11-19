# 2026-11-07 — autokernel (AutoKernel session wrap-up)

## Surface proofs (gfx90a low-level tier, AK-GFX90A-ASM-SURFACE)

| Row | Outcome |
|---|---|
| `ak-surface-proof-b-20261106` | COMPLETE, SURFACE_E2E_OK, correctness PASS (stock FA hsk128 585/585, cases 6/6, killswitch 6/6). Hand-asm gfx90a FA (asm_artifacts `.co`, source-patch.v2) built, loaded, verified and timed end to end. |
| `ak-surface-proof-a-20261106` | No GPU result. iglp0 built ok (230 s); `iglp_opt(1)` drove clang-18 device compiles of mmq-instance-iq1_s/iq2_s to 37 min, 222 GB and 124 GB RSS; stopped via STOP + SIGKILL of own PIDs. `iglp_opt(1)` in mmq-vec-dot.cuh is compile-pathological on gfx90a. |
| `ak-surface-proof-a2-20261107` | Published: C6 vs iglp0 only, reuses iglp0 build, min window 5400 s; smoke queued. |

Proof B diagnostic medians (us, n=5), C6 vs h5:

| Shape | C6 | h5 | Ratio |
|---|---|---|---|
| heads16 kv512 | 200.8 | 91.3 | 2.20x |
| heads16 kv4096 | 1066 | 475.7 | 2.24x |
| heads16 kv16384 | 4020 | 1788 | 2.25x |
| heads32 kv512 | 298.2 | 115.8 | 2.58x |
| heads32 kv4096 | 2076 | 516.9 | 4.02x |
| heads32 kv16384 | 8059 | 1887 | 4.27x |

h5_off == C6 within 0.1% (killswitch falls back). Caveat: heads32 ~= heads16 time at kv16384, so check before any keep claim (filed AK-H5-VERIFY). Surface proof only, NOT a keep claim. Result: `/mnt/raid0/llm/tmp/ak-surface-proof-b-20261106/out/RESULT.json`. AK-GFX90A-ASM-SURFACE stays open: its done bar needs an actor-generated candidate (a loop run).

## Tooling (research repo, epyc-inference-research main)

| Commit | Change |
|---|---|
| `0dc9f5c14` | build RLIMIT_AS/CPU ceiling in `execution/worktree.run_build` |
| `8101ea8eb` | per-process cap = 256 GiB whole-build budget / jobs, clamp 16-64 GiB (-j8 -> 32 GiB) |
| `b74651c8a` | custody re-pin `actors.py` after review of `dd3ab6326` + `189b1d29b`; stale author-prompt order test fixed |
| `529036ed8` | `test_custody_hold` child bound to its own tree (venv `.pth` put shared clone on sys.path -> canonical_recipe foreign refusal) |

Full loop suite from a lane worktree: 6023 passed, 1 failed (fixed by `529036ed8`). Earlier runs showed 15 test_validation_final_receipt errors and one 40-min stall near test_scratch that did not recur and pass in isolation (flaky under host load ~55).

## Root work today (already pushed)

- AKX-ALL-31.GDN ticked: K=3 across CPU/GPU x f32/BF16, 0/27,262,976 mismatches; reverse-slot and key-row mutants fail; r11 receipt-ack.
- INF-82 owner/route lines on 53 open AKX boxes: ADOPT 42, RE-FILE-C7R 4, ROUTE main-inf22 3 (+LB3 co-route), ROUTE Pipeline Mgmt 3, DECLINE-recommended 1 (P4c). Triage: `/mnt/raid0/llm/tmp/akx-triage-20261107/TRIAGE.md`.
- Runtime: suspended dispatcher sessions autokernel-all-devices-all-dimensions and autokernel-cross-workload-keep-gate repointed to `autokernel-akx-program.md` / INF-82 (backup `handoff-sessions.json.bak-ak-repoint-20261107`).

## Peers

- main-inf22 corrected the H6 citation (research `cddaaf14c`; 1.017x never existed); accepted routed LB3.1/LB4/LB4.9/LB3-kernel as C8 fold candidates; wants row ids when P0d-W3-HALFB-C6 C7r re-file and the LB3 premeasure produce results.
- Pipeline Mgmt landed opencode fix `189b1d29b`; routed to them AKX-ALL-15/15a/15b + `job.py:46` entry guard (reply pending).

## Handoff changes (this wrap-up)

`autokernel-loop.md`: dated result sub-bullets on AK-GFX90A-ASM-SURFACE (rows A, B) and AK-MMQ-H3; ticked AK-BUILD-CAP, AK-CUSTODY-REPIN, AK-TESTENV-FIX (`[no-belief: tooling-repair]`); new boxes AK-BUILD-MEM-1, AK-H5-VERIFY, AK-MMQ-IGLP1-DNR (futility-only gate class).

## Afternoon (loop management and efficiency)

**Tooling handback.** PM's AK tooling work was integrated into research main (ending 40179e3f0). The full loop suite gave 6185 passed and 1 isolated-pass flake. Four boxes were ticked: CHAMPION-CONTEXT, UNSOURCED-LINT, PROF-TWO-DENOM and SWITCH-BISECT. One behaviour change: launch refuses a non-champion anchor unless `AK_NON_CHAMPION_ANCHOR_REASON` is set.

**Efficiency replays.** Both were offline, pre-registered and read-only on the DS41 store.
- **P1, typed pre-screen:** DECLINED as designed. The heads cannot decide at the planner->author seam. Route-out catches 77% of avoidable wall but refuses 5 keeps, and 19/21 avoidable rows are planner abstentions. Only a k=4 retry budget refuses 0 keeps, and it is in-sample with 93% of its catch in one row. It stays log-only. Evidence: `/mnt/raid0/llm/tmp/ak-eff-p1-replay-20261107/`.
- **P2, typed planner:** PROCEED-TO-AB on three conditions: an `exhausted` option, >=25% reserved exploration, and DNR rows kept selectable. Of 24 planner keeps, 6 were novel and 2 came from a class marked DEAD. Evidence: `/mnt/raid0/llm/tmp/ak-eff-p2-replay-20261107/`.
- **Shared finding:** the waste is repeated planner abstention on an unchanged state (13 identical calls, 3.14 h). This became the new box AK-EFF-SAME-STATE-STOP, now in implementation on branch `ak/planner-same-state-stop`. Root commit 561faee82.

**Queue.** At 16:43Z the admissions hold (ops session, set 12:52Z) was removed by another session. Proof A2 and the C7r census are grantable and waiting behind higher-ranked GPU rows.

**Filing.** PM found 1 ended-unfiled AK row: `ak-surface-proof-b-20261106`. The verdict was in the handoff (946ea35af) but the FILED receipt was missed, because `rowflow alerts --ack` does not mention it. It was filed via `file_result.py` (pass). PM is now making `--ack` warn on a missing receipt (operator-approved).

**Dispatched (in flight).** The e2e same-run-ABBA check in `serving_gate.e2e_evidence`, the AK-BUILD-MEM-1 row prep, the AK-H5-VERIFY row prep, and the AKX-ALL-LB3.2b affinity-readback fix with re-book prep.

## Evening (loop safety, admission, calibration; operator wrap-up)

All commits below are on `epyc-inference-research` main unless marked root. Full suites for the loop were run from lane worktrees, not the shared clone.

**Landed and ticked.**

| Item | Commit | Result |
|---|---|---|
| AK-EFF-SAME-STATE-STOP | `e33cf3cd1`, refined `5707436fd` (re-pins `ead06f91e`) | A lane whose planner abstained on a state key is not re-asked on the same key; typed `planner_same_state_skip`, then the lane parks. `5707436fd` scopes the park to the lane: the run parks only when every lane is parked. `retry_budget_shadow` is log-only at >=4 prior `patch_rejected` (never refuses). Motivated by 13 identical abstentions = 3.14 h. Root tick `4fabb02f2`. |
| AK-OP-E2E-PENDING | `cae39d8c3` | `serving_gate.e2e_evidence` verifies the same-run ABBA design from the record instead of hard-coding it; unpaired, separate-run and fixed-order rows stay `pending`. Root tick `a30fe410a`. |
| AKX-ALL-LB3.2b | `6d75bd331` | Root cause was the pair harness `control_checks.py:affinity()` reading the main-TID mask after OMP pinned it (not llama.cpp). Process-wide two-snapshot readback committed as `scripts/benchmark/akx_lb32_affinity/`. Fixture under the recipe OMP env: legacy rc=68, v3 rc=0. Pair `akx-lb3-2-cv6-pair-20261107` re-booked (r2 spec queued). Root tick `315eb9771`. |
| AKX-AUTO-7 | `c8b3cbbc5` | Drain needs `--confirm-drain <lane>`; drain stays terminal (guard option, no resume path). Root tick `6366ad1eb`. |
| AKX-P4c, AK-EFF-P1 | root `c9d2a4bc7`, `561faee82` | Both declined with reasons (P4c is a duplicate pointer to SC81; P1 declined by the offline replay). |

**Landed, parent box stays open.**

| Item | Commit | What remains |
|---|---|---|
| AKX-P1d fixtures | `be1b808e3` | 17 control fixtures; found and fixed a `footprint.py` bug (comment hunks produced phantom dispatch sites and env-knob reads). Live half and the production classifier (AKX-P1e) open. |
| AKX-P5a module | `65cc983bc` | `loop/forward_admission.py` + 16 tests: structural evidence only, closed schema, mandatory expiry. Wiring rides with P1e. |
| AKX-ALL-31 gates | `c27655708` | `loop/numerics_gates.py` + 10 tests, opt-in (`NUMERICS_GATES_DEFAULT = False`). Native CPU/HIP leg, `gates.py` wiring and the default-on ratification are filed as child boxes (below). |
| Hermetic tests | `b420fa015` | Tests no longer need `EPYC_ROOT` in the caller env (10 `test_actor_context` failures + 1 collection error without it before; 88 pass, 1 skip after). |
| Harvest #3 | `13b9e8f86` | main-inf22 H16 M=36 op-futile negative, H17 profile, LCATTN seeds into the planner context. |
| LOOP-SAFETY-C C2a/C2b + D-A3 | `86319c468` | Refuse missing store or inbox; ranked path keeps the pinned `keep_candidate`. Landed in the same window under the operator's no-autopilot instruction. |

**In flight (NOT landed, nothing ticked).**

- AKX-AUTO-4 floor self-check: branch `ak/akx-auto4-floor-spread` (research `854aadbab`, `e4560c879`, `4047d8584`; wired before both source-floor writes, `run.py` re-pinned). Full suite log `/mnt/raid0/llm/tmp/ak-auto4-suite-20261107.log` was about 62% through with one `F` seen; not yet judged as pre-existing flake or regression.
- SL-2 / SL-4 serving gate: branch `ak/sl2-sl4-serving-gate` (`a07b3ace4`, `f12fa6c0d`, `4418500c6`). Awaiting rebase on current main, the `run.py` 5-hunk diff, custody re-pin and the suite. The M1 floor-row package `/mnt/raid0/llm/tmp/ak-sl2-m1-floor-20261107/` publishes only after SL-2 lands (it changes the calibrated metric).
- DF2-20: `df2-20-correct-20261107` published; the cost row waits on ROWEXACT_PASS. Cost number is an upper bound (k single-column passes).
- Queued rows (published, armed, ready): `ak-surface-proof-a2-20261107`, `inf75-c7r-w3-halfb-census-20261107`, `ak-h5-verify-20261107`, `ak-build-mem-1-20261107`, `akx-lb3-2-cv6-pair-20261107-r2`.

**Handoff changes (root).** Ticks: AK-EFF-SAME-STATE-STOP, AK-OP-E2E-PENDING, AKX-ALL-LB3.2b, AKX-AUTO-7, AKX-P4c (declined), AK-EFF-P1 (declined); all carry `[no-belief: ...]` or `[belief: cc]` tags (checked with `belief_capture_check.py`; the three advisory warnings in range belong to other sessions' files). Added in this wrap-up: AK-TESTENV-HERMETIC and AK-HARVEST-3 (done boxes), AKX-ALL-31.NATIVE / .WIRE (open), in-flight notes under AKX-AUTO-4, SL-2 and SL-4.
