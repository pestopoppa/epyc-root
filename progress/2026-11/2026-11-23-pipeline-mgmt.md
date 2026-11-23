# 2026-11-23 — pipeline-mgmt

Operator-invoked `/wrap-up`. Sources: root/research git logs (every SHA below verified in git), the Codex lane reports
(`/mnt/raid0/llm/tmp/codex-lanes-20261123/`), `/mnt/raid0/llm/tmp/ak-failure-audit-20261123/REPORT.md`, the disk reports named below.

## Keeper and rowflow (`scripts/coordination/rowflow`; deployed live unless noted)

| Change | Commit |
|---|---|
| complete-suspect guard (instant rc=0 `reason=complete` ends) | `487e9903f` |
| quiet-host gate, short GPU smoke slot, supersede block | `bafa78f11` |
| `file_result` falls back to `<workdir>/out/RESULT.json` | `85ba6d0b8` |
| GPU grants bandwidth-heavy only if they declare it | `b45c9efd6` |
| QUIET-RESERVE: waiting quiet rows hold the host | `eda64e372` |
| QUIET-SERIAL: one quiet row per socket, shortest estimate first | `09e637670` |
| disk hardening: DISK-WARN floor+40G, 2 h idle reap under 200G, LARGE-DERIVED, `worktree_gate by-owner` | `0514eecda` |
| LIGHT test claim (`claim --build --light`) on 84-87 | `2f6e24fa9` |
| BUILD LANE / build-window (refused build claim >15 min holds new quiet grants) | `658c64cec` (deploy in progress: unit tests 1188 passed, replay gate running at wrap-up) |
| earlier: launcher emergency / shape widening / idle_crash_exempt / autorequeue_max / E5 starvation / code-budget redesign | `f5a2034fe` / `db0da782b` / `c514779d1` / `27d4d126c` / `8c0aad249` / `48997f7f0` (research) |
| row publishes refused when they fail AK lint | `009c15e3d` |

**In progress, not landed:** B2/B4-B14 of the AutoKernel failure audit (box `PM-AKAUDIT-B1-B14`); reaper rule fixes (`PM-REAPER-RULES`,
branch `pm/reaper-rules-20261123`); PII hook ratify package `/mnt/raid0/llm/tmp/ratify-pii-capsule-20261123/` (box `PM-PII-CAPSULE-RATIFY`, needs an operator signature).

## AutoKernel loop-infrastructure boxes (handoffs/active/autokernel-loop.md)

Research repo unless noted. AK-DEADCODE-DELETE `a9d9e86c0` + `249a27960`; AK-SPLIT-CAMPAIGN-CONTROL `8ed247d40`; AK-SPLIT-ACTORS `03b1f58be`;
AK-SPLIT-SCHEDULING `85ba0c0d0`; AKU-23 `6fcf16370`; AK-PARETO-RETAIN-WIRE + gates.py F821 `0961ed848`; AK-TEMP-AXIS-1..5 research `892ad9282`..`e22b7766c`, root `b2e80deec`;
OAB-6 `36cb8908b`. Codex: AKU-01 `5c6977d3a`, AKU-02 `f55fe0b8f`, AKU-03 `66483b07f`, AKU-05 `87429c210`, AK-TIMING-ZERO-1 `a84600e30`, AK-RECEIPT-ARMS-1 `e3a379869`
(177 retained receipts refused at first failing check, none rewritten). Earlier: CTC-2-TI, AKU-17/18/20/21/22/25/10g2, AK-CENSUS-UPDATE-SHAPES, AK-TRIM, AKPL-P4.

Corrections made at wrap-up: AKU-20 and AKU-21 carried a tick suffix but an open `[ ]` (flipped to `[x]`); the AKU-23 tick overclaims, so a dated note
records that the arm-seconds budget wiring is still open (utilisation is wired, budgets are not counted in arm-seconds). OAB-8 / OAB-16: offline tests only, live run open, neither ticked.

Codex lanes: cx6 landed (see above). cx8 (SPEC-PIT.1 temperature-gate integration, research local `bfd15695b`, root local `14dd32bfc`, 71 tests pass) is NOT pushed:
`check_regrowth_guards.py` reads 127623 lines vs the protected 127259 ceiling (origin/main was already 338 over); box `PM-CX8-SPECPIT-PUSH`. cx4c, cx5c, cx7 had no report file at wrap-up.

## Taskflow canary

r8f filed FIX-HARNESS 4/10 (`76ec1a18e`). r8g harness fixes `9d7e102c6`, `f0ee5a168`, `c6ea4fa42`, `b60f9862d`, `6694fcf50`, `8f46306e2`, `ccb51d59e`; r8g was published, then stopped
to yield to quiet rows, and is resumable (note added to the RTG100 canary box in churn-pipeline.md; no tick, not saturated).

## Disk

`/mnt/raid0` 154G to about 440G free. Root cause of the root-repo bloat: PII pre-commit capsules (one per commit, ~30 MB / 4,222 files each, no retention):
9,095 clean capsules deleted (98.6 GB, 25.4M files; kept 1,469: findings 685, receipt-less 65, recent 719), `.git` 223G to 38G, safe repack without gc. Secondary: whole-file history of
`research/intake_index.yaml` (616 MB packed) and large handoffs. ~33 worktrees removed; tmp stale sweep in `/mnt/raid0/llm/tmp/tmp-stale-sweep-20261123/`
(530 GB measured; 93 GB reclaimable; 65 GB pinned by a reaper rule). Reports: `/mnt/raid0/llm/tmp/root-git-bloat-20261123/`. Lessons filed in
`.claude/skills/inference-backlog-scheduling/references/disk-bin.md`.

## Operator decisions today

E5 deferred to 2026-11-24 on champion C18 (r9 package `/mnt/raid0/llm/tmp/inf45-e5v2-stageb-r9-20261123/`); Codex allowed for loop infra; PII capsules 2-day retention plus hook fix;
safe repack approved; reclaim the maximum safely allowed.

## Wrap-up gates

Ticks added by this wrap-up: 0 new result ticks (2 checkbox flips: AKU-20, AKU-21; both `[no-belief: software]` already on the line). New boxes filed: 5
(`PM-AKAUDIT-B1-B14`, `PM-REAPER-RULES`, `PM-PII-CAPSULE-RATIFY`, `PM-BUILDLANE-DEPLOY-VERIFY`, `PM-CX8-SPECPIT-PUSH`). Index prune diff prepared, not applied (operator applies).
