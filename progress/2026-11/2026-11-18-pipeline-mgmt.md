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
