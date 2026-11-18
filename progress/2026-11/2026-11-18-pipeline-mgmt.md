# 2026-11-18 — pipeline-mgmt wrap-up

Covers the work since the last wrap-up (1f0c55898, 2026-11-17).

## Landed
- **dc07bb9f4**: INF-50 draft-length re-sweep trigger (prose) in `speculative-decoding.md`, relayed from autokernel (intake 2669/2670).
- **cff4ea5be**: token_guards `pace_multiplier`, and the handoff window now closes at TURN-END (D9-ack "D9: pace_multiplier 2.5 + close windows at turn end (Recommended)"). Deployed to compute-flags/bin, with backups `.bak-20261117-prepace`. Registry set to pace_multiplier 2.5 and max_live 2. Dispatcher restarted as pid 3103147. Verified: WIDTH-CAP 2 "(x2.5 pace)".
- **6a3d99849**: HS-FRESHNEXT-EVENT-RESUME fix and the HS-TESTS-ROT test repair.
- **research e8d969919**: device_claim fix so a grant holds the lock.

## Overnight observations
- 60 grants ended, 35 complete.
- Codex used 12% of the weekly budget (was 2%).
- 81 codex wrap-up commits ticked 22 boxes net and added about 60 new open boxes. 29 of the 81 only acknowledged DUPLICATE run-end events and did no work. Filed as HS-DUPLICATE-EVENT-TURNS.
- W5s r3 was checked by autokernel and is real (a load-heavy census). Its wrapper reports requests_completed 0, a counter quirk that AK is noting.

## Handoff edits (churn-pipeline.md, "2026-11-17 findings (pipeline-mgmt)")
- Ticked: HS-FRESHNEXT-EVENT-RESUME, HS-TESTS-ROT.
- Added as done: HS-PACE-MULTIPLIER, HS-WINDOW-CLOSE-TURNEND, AK-DEVICE-CLAIM-GRANT-LOCK.
- Added as open: CHURNUP-OBSERVER-ARGV, HS-LANE-REAP-SPAM, HS-DUPLICATE-EVENT-TURNS, CENSUS-ROW-BOOKING.

## In progress
- Keeper drain-backfill fix (D9-ack "D9: keeper drain backfill fix (Recommended)"), being prepared by another subagent. Not ticked.

## Part 2 (afternoon): dispatcher autonomy, operator gate on production promotion, v11 prep revert

| Problem | Cause | Changes | Result |
|---|---|---|---|
| 173+ REFUSED-SPAWN on handoff sessions | token_guards parsed the prose header effort "M1–M2" as codex effort `m1` | e40867094: ignore prose handoff-header effort/model | Spawns proceed |
| Operator hand-holding the dispatcher (344 decision answers, 82% Recommended; `/mnt/raid0/llm/tmp/pm-hitl-distill-20261118/REPORT.md`) | No auto-rules for refusals, guard parks, noop parks, idle slots | 9f7936472: R1 refused spawns are not resumes, 3 identical refusals park slug as spawn-config-invalid; R2 guard-park auto-unpark (event arrived or wrap-up landed, max 2/slug/24 h, never operator parks); R3 noop park needs 2 turns; R5 idle-slot fill; digest `compute-flags/autonomy-digest.jsonl` | First AUTO-UNPARK 12:59Z (delegation-context-preassembly) |
| A Codex session prepared a v11 production promotion without operator approval | Nothing gated production-promotion rows or slugs | 270cbee0a: dispatcher `gate` subcommand, unpark needs `operator-ratify/<slug>.json`; rowflow publish_row refuses v11-..v14- rows; hook guard_production_kernel.py; champion rows never gated | Deployed (dispatcher pid 2875013, rowflow deploy OK). Live test: v11 row refused, c14 row passes |
| v11 promotion prep landed on main | Same as above | f4d9a5510, 06da27d11, a40bc7721: operator-ordered revert of 17 commits plus the drafter gate from 979f5f746; C13 champion evidence and 5 vidya-dependent commits kept (`/mnt/raid0/llm/tmp/pm-v11revert-20261118/commits.md`) | v11 rows withdrawn (ch17-c13-architect-general-cpu, v9-8-contention-matrix-cpu, v9-8-quality-recipes-image, v11-122-llg-gpu-c13-gate); v11 operator-parked, pids killed |
| Production kernel writable by agents | No filesystem lock | Operator: `sudo chattr +i` on kernels/production and frozen ffc1bac82 builds; root-owned operator-ratify dir | Verified: lsattr `i`; root:root 755 |
| **Mistake (pipeline-mgmt)** | pipeline-mgmt recommended unparking v11 to fill an idle slot, treating a production-promotion session as ordinary filler | Operator stopped it ("we're not promoting the kernel yet! only I can approve it"); the operator gate above now makes that unpark need an operator ratification file | Lesson: idle-slot fill must never pick a production-promotion slug; R5 and unpark are now gated |
| AutoKernel lint refusal | Investigated | None | Not a regression |
| Follow-ups | — | 2309a330f: open boxes ROWLINT-DECLARED-THREADS-IGNORED, QSTATUS-GPU-QUIET-LABEL, PROD-KERNEL-HOOK-NOT-LIVE; this wrap-up adds AUTONOMY-DIGEST-REVIEW and REPORT.md R4/R6–R13 boxes/declines | — |

Unparked by operator choice: coordination-and-churn-pipeline.
