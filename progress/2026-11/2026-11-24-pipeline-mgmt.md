# 2026-11-24 — pipeline-mgmt

## Overnight 2026-11-23/24 — AutoKernel support (keeper/rowflow)

Continues `2026-11-23-pipeline-mgmt.md`. All SHAs on origin/main.

| Change | Problem / root cause | SHA | Live status |
|---|---|---|---|
| Keeper batch B1-B4, B8, B12-B14 (AK row-failure audit) | AK rows failed on keeper-side gaps (GPU host cores held after server exit, build claims blocking q3, short rows unslotted, WS58_CPUS non-digit, launcher.out lost) | 4b48a8ed2..929ac6acf (HOLD-ORPHAN skips unstarted grants 77fa04d51) | live via d172d9eed |
| GPU attribution via FILLER_ID; queue_status uses the keeper predicate | queue_status and keeper disagreed on GPU busy | a348c1816 | live |
| SMOKE-NO-MEASURE warn-only | AK rows lacked smoke_measure.json; enforcement failed them | eca36d583 + 290799730 | live 22:57Z |
| declared_threads beats launcher argv re-scan | keeper re-derived the wrong width from launcher argv | 748318efb | live (deploy 9d85d25aa) 23:28Z |
| QUIET-SERIAL covers all quiet classes; exclusive_cpu opt-in | quiet rows co-granted | 5bd499aec | live |
| B8 revert: OWNER_STOP_REQUEUE=False | B8 requeued AK's paused rows beside the gate row | 4814a9b70 | live |
| Reaper hk_heavy on 84-87, nice 19, ionice idle, REAP-DEFER-QUIET | reaper ran unpinned beside quiet r4 02:53-03:28Z | d3e35a502 + 5fc893040 | live, verified 05:26:59Z |
| SMOKE-NO-MEASURE warn-only again | Codex cx7 cba16d6dd re-enabled enforcement; failed AK calib-c18-r2 | f9d96affb | pushed |
| Accept `<scratch_root>/out/smoke/smoke_measure.json` | AK SPEC-PIT/calibration jobs write there | 3a8c1a743 | pushed |
| AK CPU rows quiet by default (no requires_quiet_host key) + test fix | manifests lacked quiet keys | 57f4f951e | deploy in flight: at wrap-up `/mnt/raid0/llm/tmp/pm-deploy-smw2.log` was at "unit tests (128 files)", no "live" line yet |
| Index RTG-100 next action | — | pushed earlier | — |

Earlier-day items now closed: rowflow BUILD LANE 658c64cec deploy log reports `658c64cec… live`, rc=0
(PM-BUILDLANE-DEPLOY-VERIFY ticked). PII capsule package applied by the operator, landed 5082c73be: new
capsule 2.4 MB, prune removed 51; `custody_format 2` on origin/main, `pytest scripts/hooks/tests -k pii`
152 passed (PM-PII-CAPSULE-RATIFY ticked).

### Incidents

- AK row r3 crashed on its own TypeError (job-side, not keeper).
- B8 requeued AK's paused rows beside the gate row → reverted 4814a9b70.
- Quiet rows were co-granted because their manifests lacked the quiet keys → 5bd499aec, 57f4f951e.
- Reaper ran unpinned beside quiet r4 02:53-03:28Z → d3e35a502 + 5fc893040.
- q1/q2 idle 00:25-06:30Z at AK's request without asking the operator; operator flagged it. Lesson: ask
  the operator before deliberately idling quarters.
- GPU queue ran dry 04:26-06:26Z while AK was blocked on an operator question.
- Codex cx7 (4c3a1b942, cba16d6dd) broke the deploy gate and re-enabled enforcement against the agreed
  decision. Lesson recorded in `.claude/skills/inference-backlog-scheduling/references/incident-ledger.md`:
  Codex lanes must not change keeper policy constants or the tests that pin them. cx7 and cx8 have exited.

### Boxes filed (coordination-and-churn-pipeline.md)

PM-ROWFLOW-RELEASE-BUILD, PM-SMOKE-ENFORCE-REENABLE, PM-KEEPER-REAP-QH-TESTS, PM-PUBLISH-REHEARSAL,
PM-RULES-WARN-FIRST, PM-SHARED-CLONE-SYNC (operator-decision), PM-SCRATCH-PINS-DRIFT (operator-decision).
PM-AKAUDIT-B1-B14 stays open (B5/B6, B7 enforcement, B9-B11 neither landed by pipeline-mgmt nor declined);
PM-REAPER-RULES stays open (reapsim re-run not recorded); PM-CX8-SPECPIT-PUSH blocked on the code-budget
ceiling (operator decision).

## Operator /wrap-up 2026-11-24 — filing audit of the day's pipeline-mgmt work

All SHAs below verified reachable from origin/main (root unless noted).

| Item | Box | Status | SHA |
|---|---|---|---|
| Keeper/rowflow fixes (QUIET-SERIAL urgent-first, no grant onto build claim, keeper re-pin, EASY-backfill reservation + replay fixtures, LIGHT-POCKET, smoke_verdict/supersedes_check/owner_watch, rc75 NO-REQUEUE-COMPLETE, BUILD-INTERSTICE, SLOT-KEEP, complete_check, rerank, GPU-HOST-FOREIGN) | PM-KEEPER-FIXES-1124 (new) | filed + ticked | 929ac6acf 3f1101c71 ce08516f3 5fc893040 1cd1d5cb8 eb643ac37 49f6a9f17 20a74f6ff d5d0f3450 460e0696b 544ca0b4a 513ef7a02 f95b97193 fd1e4001c 4a0d5a2f9 04d40f485 a281def6b 1527a5a02 ed53a2c2f 2fc1818a5 (live) |
| Row preflight lane, 12 checks | PM-PREFLIGHT-12 (new) | filed + ticked | bb5c756d0 2099822d9 8835cc392 |
| Re-planning scheduler C (shadow) | PM-REPLAN-C-SOAK | noted, open (7-day soak) | 5851284db, design afddb8c5e, vidya 9544bddd0 |
| Codex lane driver | PM-CODEX-LANE-VERDICT | noted, open: done-when `-k codex_lane_verdict` selects 0 tests; test_codex_lane_drive.py 7 passed | 5908a883f |
| TF-R8G-PATHSPEC-LRANGE / REVIEWER-CONTROL | churn-pipeline.md | verified ticked with belief tags | fc6f16336 (fix 3b11e6c82) |
| TF-R8G-REFUSAL-HINT | churn-pipeline.md | noted, open (r8h owner-STOPped, after AK CPU queue) | 3b11e6c82 |
| churn.loop.json | — | landed | cc6647e03 b7948fa3e |
| Intakes always-on 2942-2955 Stage 4, 2863, 2864 | — | landed | 9db462df8 8bc550ef5 |
| Research (AK spool / UTF-8 encoding) | — | landed (research repo) | 0403f49a7 9d180ad29 |

In flight: Codex cx12 TF-EARLY-END-CENSUS reports DONE on branch `cx12-census` ab5e9f6e7 (verdict DECLINE, 0/50 early ends), not pushed. Quiet-model package waits on AK rows ak-pernuma-contam-cpu-20261124 and ak-gpu-cpuload-contam-20261124.
