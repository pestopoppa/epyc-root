# Progress — 2026-07-05 — AutoPilot dashboard stale-panel root cause + transport hardening

Scope: the orchestrator AutoPilot dashboard at `:8000/dashboard`
(`epyc-orchestrator`). Operator report: live inference tap, cpu regions lock,
and topology panels stale AGAIN ("why does it keep breaking?").

## Root cause (verified live before any edit)

**Every backend producer was healthy** (tap events 0–4s old, locks/topology
recomputed live, health `ok`, all endpoints 200-fresh). The recurring failure
is in the *delivery path*, structurally invisible to the health guard:

1. **One failure domain for exactly the trio.** `snapshot()` builds
   topology + region_locks + activity via `_poll_all_slots()` (~29-port
   fan-out with NO overall deadline; host loadavg ~78) and
   `_region_locks_payload()`; commit `f6209d78` (06-28) made the tap enrich
   recompute the same functions per SSE tick. One stall stales all three
   panels while independently-polled panels stay live.
2. **Client wedge states.** The 2.5s snapshot poll had no fetch timeout and a
   jam-forever in-flight boolean; the monotonic frame watermark fell back to
   the CLIENT clock on a malformed payload and was never reset (one poisoned
   value silently drops every later snapshot); tap content was SSE-only; tap
   badge was fed from a different source than tap content.
3. **The recurrence driver: AutoPilot restarts the :8000 API at EVERY trial
   boundary (~20–25 min)** — observed live (PID 2632834→2678192 at 17:19:48).
   Each restart tears down SSE + in-flight fetches: a repeated dice roll
   against the wedges above. Any long-open tab eventually froze the trio.
4. **Health blind spot.** `/dashboard/api/health` only statted producer files;
   `topology`/`region_locks` had zero gating sources → could never report
   anything but fresh; serve-path hangs/exceptions invisible.

## Delivered (epyc-orchestrator, 9 slices, all tested + deployed)

Design rule: every failure self-healing or loudly visible; no silent freezes.

| Commit | Slice |
|--------|-------|
| `1cea531a` | Client wedge-killers: `fetchJSON` (AbortController) on the snapshot poll, self-expiring in-flight guard, no-client-clock watermark + resets, watchdog `snapshotTransportWatchdog` (rebuild stream + poll if no snapshot applied >15s; visibilitychange/online hooks), guarded legacy SSE reconnects |
| `856e3b3d` | `_poll_all_slots` overall 2.5s deadline + `slots_poll_meta` in the snapshot payload (degradation rendered, never silent) |
| `4bc5abc2` | Serve-path decoupling: `_region_locks_cached()` (1s TTL, fail-open last-good), `_port_roles_cached()` (2s TTL over ps scan), tap enrich fails open to unenriched requests |
| `09e220e2` | Tap rotation-proofing: shard-aware `_latest_tap_events_mtime` (base missing between rotation and next append), stitched `.1` tail reads, client tap fetch-fallback when SSE silent >6s, tap badge unified with tap content frames |
| `1e53764b` | Health serve-path coverage: per-worker `_SNAPSHOT_BUILD_STATS`, `serve_path` block (stale on hang >30s or crash loop), `?probe=snapshot` real-build check |
| `e59bfa25` | Chaos test `tests/integration/test_dashboard_restart_recovery.py`: real uvicorn SIGKILLed mid-SSE → fresh snapshot + reconnected stream + healthy serve_path within 15s |
| `216d089a` | Audit fold-in: dead v6 `/slots` prompt/content reads deleted (+ `_find_slot_by_objective` removed), honest `extern_<port>` fallback labels, **MI210 :8802 = first-class `mi210_gpu` role** (kind `gpu-llama-server`, GPU chip in strip — operator-decided; slot activity now, token tap once stack-routed), 5 panels registered into health (pareto, repo_readiness, optimization_brief, insight_graph, build_rev), bare `catch{}` → self-clearing in-panel error chips |
| `53802dbd`+`581caccc` | All remaining pollers → `fetchJSON`; 45-day-stale "current prompt" header suppressed unless <1h old (age chip when shown) |

Validation: 186 dashboard unit tests + 2 integration chaos tests green; ruff,
py_compile, `node --check` per slice; explicit-pathspec commits (parallel
agents' stack files untouched); GitNexus impact checks run pre-edit
(`_poll_all_slots` HIGH — contract preserved) + index refreshed.

## Deploy + live verification (runbook)

- `AUTOPILOT_TOOL_SENTINELS=1 orchestrator_stack.py reload orchestrator
  --profile gate3-tool-telemetry` → new API PID `2839729` (verified changed),
  health 200.
- `/dashboard/api/health`: `ok`, **14 panels** (was 9), `serve_path` fresh
  (build 1.85s). `?probe=snapshot`: ok in 0.41s.
- `slots_poll_meta`: 29/29 ports answered in 0.018s.
- `live_busy_by_role`: **zero malformed `port_NNNN(model)` keys**; `mi210_gpu`
  present. Topology: `{port_8802, role=mi210_gpu, kind=gpu-llama-server,
  model=Qwen3.6-35B-A3B-MTP-Q8_0, running=true}`.
- Multiplex delivers 8 snapshot events / 8s (full 2 Hz; ~0.5 Hz before the
  fan-out deadline).
- Browser-tab self-heal after an API restart is watchdog-driven (≤15s);
  operator should hard-refresh once to pick up the new JS, after which
  reloads/restarts require no manual refresh.

## Operator decisions honored / still open

- MI210 dashboard visibility: DONE (decided this session). Managed-role
  registry listing remains an integration-time step via `stack_change_pipeline`.
- Open: AutoPilot per-trial API restart cadence (dashboard now tolerates it);
  retiring the dead `autopilot_prompt_tap.txt` writer; `contention_matrix.yaml`
  refresh (8.4d old, non-gating); Playwright for browser-level chaos automation.

## Second wave (same day, operator-approved follow-ups)

- **prompt_tap surface retired end-to-end** (orch `87c5f970`): no writer has
  existed in-repo for months; removed the `current_prompt` fields (fetch +
  legacy SSE), the panel source, the client block, the path constant, and the
  45-day-stale file itself.
- **Regions Lock panel fold + orphan inference cards** (orch `9ade5019`,
  operator request): panel renamed `regions lock` (CPU region locks + device
  occupancy); GPU/extern servers render as spanning device rows in both grid
  paths; live tap panel shows "orphan inference" cards for active slots on
  off-pipeline servers (MI210 direct-access traffic — slot id, token counts,
  model; explicit "no token tap — off-pipeline" label). A non-OK contention
  matrix now renders as a loud incident line in the gate strip. Verified live:
  `mi210_gpu` kind `gpu-llama-server` n_active=1 flows through the snapshot.
  HTML is hot-read — visible on tab refresh, no reload needed.
- **No-op API restart guard** (orch `b1a21e79`): `EnvRestartApplicator` reads
  the live uvicorn parent's `/proc/<pid>/environ` and skips the restart on a
  positive full-key match (fail-safe toward restarting on any uncertainty);
  `api_restart: performed|skipped_noop` rides into the journal as an eval
  covariate; `config_applicator.py` added to the phase-health runtime-source
  drift list. Live at the next AutoPilot launch (daemon down since 18:46:52).
- **Contention matrix**: handoff `handoffs/active/contention-matrix-v6-quarter-refresh.md`
  created and ownership passed to the parallel codex session (operator-directed).
  Codex finding: measured-role hash `df373c79cc4af06f` still matches — the
  stale verdict was a hash-scope false positive (live hash wrongly includes
  the auxiliary `eval_batch_frontdoor`); fix owned by codex, NOT this session.
- Deploy state: dashboard.py server-side changes from this wave (prompt_tap
  field removal) await the next API reload — deferred to avoid racing the
  codex session and the in-flight seeding sweep; client no longer reads those
  fields so nothing is user-visible in the interim.
