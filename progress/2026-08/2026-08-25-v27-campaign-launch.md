# 2026-08-25 — AutoKernel v27 session wrap-up: campaign LAUNCHED

## Outcome

The v27 terminal is **achieved as a launch**: the ten-science campaign is **LIVE** under
supervisor session `ak-53087cbd7a1928c71d5831cb` at
`/mnt/raid0/llm/autokernel/deployments/gpu-discovery-quant-ladder-occupancy-v27`. All six
restart-order items are complete; science is **0/10** at launch and the AK-V27-10 checkbox stays
open until ten unique scientific dispositions complete without a crash. This record is the
full-session wrap-up: the complete arc, the launch identity block, the monitoring contract, and the
"what remains" list. It was prepared in the isolated root lane
`/mnt/raid0/llm/worktrees/mains/root-autokernel-wrapup-20260822` (branch
`codex/autokernel-wrapup-20260822`); the owning session applies the index/handoff edits and owns the
commit. The live campaign deployment was never written into; no inference, GPU work, or build ran;
the shared `/workspace` checkout was not touched (all work confined to `/mnt/raid0/llm` per operator
directive).

## Session arc (all on record)

1. **C6 trust boundary**: commit `3fc7868c` (native oracle/candidate split) — independent audit **GO**
   with 3 low defects (D1 untyped AttributeError escapes on malformed manifests; D2 leg-argv path
   fields tautological at reopen; D3 per-leg residency kfd_pids not cross-bound to child_pid). All
   three fixed on the descendant (`27602b14`).
2. **Cumulative authority journal**: commit `b12de815` — independent audit **GO** with 1 moderate
   defect (D1-PERF: journal+lock broke `_is_resumable_stage_root` → mid-run crash parks operations in
   ambiguous; D2 LOW + D3 cosmetic also noted). Fixed on the descendant (`27602b14`); all eight
   original `5be84b4a` findings verified fixed.
3. **Descendant**: `codex/autokernel-v27-descendant-20260823` @ **`cfa8a0d8`** — merge `bd352166`
   (C6 live split + cumulative authority journal on audited foundations) + audit fixes `27602b14` +
   DeepSeek backup critic `9b200b6f` + trust-anchor bump `c8cf66ee` + wrapper pin `cfa8a0d8`.
   **286/291** tests + **54/54** factory after the operator-approved 2.1.231 → 2.1.241 bump.
4. **Dashboard**: `codex/dashboard-v27-support-20260821` @ **`b12a32fa`** (v27 final producer schema,
   all v27 pins unset, test-asserted) — independent audit **GO** (2 LOW observations; fail-closed
   state visible). 362 tests pass.
5. **OP-12/15 ratification package** prepared:
   `artifacts/operator/op12-op15-ratification-package-20260823/` (README.md, report.md,
   `ratify_op12_op15.sh`) in the lane; the `/workspace` convenience copy was removed per the sandbox
   boundary. Operator runs `./ratify_op12_op15.sh`.
6. **Reclamation preservation**: 5 unique uncommitted deltas captured as patches at
   `/mnt/raid0/llm/autokernel/preserved-uncommitted-20260823/` (MANIFEST.md + 01–05), including the
   **OP-11-gated vecdotq sources** (patches 03/04, preserved but explicitly not committed).
7. **G-series (operator-approved GPU block)**:
   - **G15 CLOSED as a search screen**: full-model prefill ≈ **+7.1% @ p8192** (below the ≥8% gate —
     physics pass / decision fail), **retained as a measured candidate lever for the v27 aggregate
     composition per operator ruling**. `GGML_CUDA_DELTANET_MIN_BLOCKS_PER_SM` is a COMPILE-TIME
     macro (build-time `-DCMAKE_HIP_FLAGS=...`), not a runtime flag.
   - **G16 PASS**: NMSE < 1e-7 at every shape, incl. chunked H=32/d=128 through 8192 tokens (57/57).
   - **G10 eval run complete**: 20/21 + 1 not-supported + **1 marginal f16-KV FAIL** at
     hsk=256/kv=20000/nb=512 (filed for follow-up); the "64 pre-existing FA FAILs" resolved as the
     ROCWMMA-off fallback defect — absent on the production binary.
   - **G6 verdict (b)**: no torch ≥ 2.7 for ROCm 6.2 — **ROCm raise scheduled into the next
     production promotion** (required for DFlash2, ~70 t/s on Qwen3.8-27B), per operator ruling.
8. **Backup critic**: DeepSeek V4 Flash via the opencode CLI (`deepseek/deepseek-v4-flash`),
   failover wired into ClaudeCritic; node-owned wrapper pinned at
   `/mnt/raid0/llm/autokernel/bin/opencode.exe` (**1.18.18** verified).
9. **Restart-order item 5 COMPLETE**: initialize (`inference_executed=false`) + validate-only ×2
   **IDENTICAL** at the deployment (identities below).
10. **CAMPAIGN LAUNCHED (restart-order item 6)** — identity block below; first operation in source
    materialization; science 0/10 at launch.
11. **Boundary correction**: all work confined to `/mnt/raid0/llm` (operator directive).

## Launch identity block

| Element | Value |
|---|---|
| Deployment | `/mnt/raid0/llm/autokernel/deployments/gpu-discovery-quant-ladder-occupancy-v27` |
| Descendant | `codex/autokernel-v27-descendant-20260823` @ `cfa8a0d8` |
| Supervisor session | `ak-53087cbd7a1928c71d5831cb` (`spec_sha256` `53087cbd7a1928c71d5831cb2b5fc8f92695d4e07b7c857e048b09ad39d28aa6`) |
| Supervisor PID | 2254279 (started 2026-08-25T15:48:29Z, tmux socket `epyc-autokernel-supervisors`) |
| Controller child | PID 2254297 (`discovery_deployment_factory`, under tmux, sealed execution closure) |
| Graph SHA-256 | `43f992dadf5148e802937365ff7c74232bfbc76477d8957bcd69be7019602963` (validate-only ×2 IDENTICAL, `inference_executed=false`) |
| Config-file SHA-256 | `14ba06073c2b5d8ccc3c74417ba1649254f7f43178df16e928202dab5c23fe5d` (`config/deployment.json`) |
| Semantic config SHA-256 | `eac81e0d4755fd61aecf7688c6fddcc5b44f109500dd628e453a3ba2fb38f6df` (`deployment_identity_sha256`, campaign id `ak-discovery-eac81e0d4755fd61`) |
| First operation | `e4411178e4045faa66c1942456446d3dd2a0a42514fb716d1e573f47b0f3087d` — `intent.json` + `source-manifest.json` written (source materialization phase; mechanism `q5_0_one_wave_per_output_block`, change-class `dispatcher`, candidate `akc-discovery-1`, declared file `ggml/src/ggml-cuda/mmvq.cu`, instrument `5bbcc549`) |
| Science | `scientific_attempts = 0` (state.json: `complete=false`, `next=1`, `iterations=[]`) |

## Monitoring contract

- **Live telemetry**: `state/state.json` — watch `scientific_attempts` (science 0 → 1 at the first
  disposition that spends a debit), `inflight`, `iterations`, `complete`.
- **Operations ledger**: one directory per operation under `operations/` — receipts materialize in
  order: intent → source-manifest → composition → correctness → attribution → runner →
  classification.
- **Claims ledger**: `operations/claims/device.jsonl` — claim hold/release posture per phase (GPU
  claim owned only during GPU phases).
- **Crash boundaries**: `state/death-ledger.jsonl` + `supervisor.log` + controller
  stdout/stderr. AK-V27-10's "ten unique scientific dispositions **without a crash**" is measured
  against this ledger: any controller death before ten dispositions restarts the count.
- **First scientific disposition**: the first operation that completes a typed classification
  (PASS / FAIL / refusal-with-debit) and advances `scientific_attempts`. Typed provider-policy skips
  and precompute refusals advance the portfolio (scheduling) but **spend zero science** — they must
  not be mistaken for dispositions.
- **Dashboard**: v27 pins remain unset; the journal trust indicator (matched / mismatched / absent →
  NOT-TRUSTED but visible) is the dashboard-side monitor of the authority chain.
- **Do not**: write into the deployment, kill or restart anything, `pkill`/`pgrep` on name patterns.

## What remains

- **10/10 science target**: AK-V27-10 stays open until ten unique scientific dispositions without a
  crash.
- **Open C6-row items** (AK-V27-C6 remainder, carried from the audit): live native Ghost Replay
  process, interposer/runtime-map authentication on the C6 path, cache-metric deny aliases.
- **G10 marginal case**: the f16-KV FAIL at hsk=256/kv=20000/nb=512, filed for follow-up (the
  ROCWMMA-off fallback defect is closed; this is a distinct observation).
- **Dashboard**: 2 LOW audit observations (fail-closed-visible posture); v27 pins stay unset until
  the producer feeds validated data.
- **DFlash2 / ROCm raise**: G6 verdict (b) — the ROCm raise is scheduled into the next production
  promotion and is required for DFlash2 (~70 t/s on Qwen3.8-27B).
- **OP-12/15 decision**: the operator runs `./ratify_op12_op15.sh` in
  `artifacts/operator/op12-op15-ratification-package-20260823/` (mapping: patch 03 → OP-15, patch 04
  → provenance-only commit, OP-12 → committed from the retained inf37-fancy-simd worktree with SHA
  verification).

## Hygiene

- Frozen production kernel set untouched (no modify/build/execute).
- No inference, GPU, or build work by this wrap-up; the live campaign deployment was read-only
  (state/identity/ledger reads only) and is running (supervisor PID 2254279, controller PID 2254297
  verified alive at wrap-up).
- No repository file modified by this session; the wrap-up deliverables are drafts in the lane.

## Campaign crash + fix + relaunch (2026-08-25)

- First launch (supervisor `ak-53087cbd…`) ran 7 iterations (critic_revise / screen_refused /
  critic_reject — zero science, `scientific_attempts=0`) then CRASHED at the 8th question
  selection: unhandled `DiscoveryControllerError: preauthored hypothesis already exists with
  different provenance` (controller exit 1; `--max-restarts 0` stopped the supervisor; death
  ledger sequence 3–5).
- Root cause: the Q5 preauthored continuation opened at turn 1 with the first-authored
  candidate's manifest; re-authoring the SAME sealed carrier at turn 8 produced a re-derived
  candidate manifest, and the provenance guard compared the full hypothesis incl. the per-turn
  manifest. The carrier provenance fields (carrier_sha256, historical_commit,
  source_backed_diff_sha256, origin/author, statement/falsifier) were identical.
- Fix `5b807bf9` on the descendant: `_ensure_question` compares only the provenance-critical
  fields — same-carrier re-authoring reopens idempotently; any carrier-field difference still
  refuses fail-closed. Regression test (re-authored manifest reopens, substituted carrier
  refuses) + pre-split call-count fixture fix in test_q5_preauthored_continuation. 372 affected
  tests green.
- The deployment identity seal correctly REFUSED cross-code resume (`sealed deployment identity
  changed`) — the crashed state (0 science) is preserved at
  `state-crashed-ak53087cbd/`; a FRESH campaign relaunched:
  - supervisor session `ak-b7736cde36f9927bf28b27d6`, controller child 3119591, execution
    closure `f570554b06…` (fixed code), deployment
    gpu-discovery-quant-ladder-occupancy-v27.
  - Re-initialized + validate-only ×2 IDENTICAL: graph_sha256
    `9732f78fe5efb57ea7932bc8cdab58ff2d89fe1a0b4920f3156268c4436aa8fd`, inference_executed=false.
- Lesson recorded: a campaign crash that requires a code change forfeits the resume (by design —
  the identity seal is the anti-substitution guarantee); the cost is re-running non-science
  refusals, never science (0/10 preserved).

## Autonomous monitoring (2026-08-26)

Operator: "monitor actively; make a cron job if need be." No crontab binary on host → detached
watchdog loop (setsid nohup, PID recorded) running `/mnt/raid0/llm/autokernel/monitor-v27-campaign.sh`
every 60 s with flock overlap protection + heartbeat at
`$DEP/watcher-heartbeat.log`. The monitor reads ONLY the deployment state/supervisor-ledger
(no pgrep/pkill), journals every change to `$DEP/monitor.log` and keeps `.monitor-snapshot.json`.
Future sessions: check `monitor.log` for the delta stream, `watcher-heartbeat.log` for liveness
(stale >2 min = watcher died), `state/state.json` for the live posture.

## Recovery chain (2026-08-26) — four environmental stops, all fixed, campaign live

1. **Planner 401** (codex token expired; 284 planner_transient rows, unbounded retry loop). Operator
   re-logged-in; the login's write window left auth.json mid-state → actor refused it → controller
   terminal failure. Operator materialized a clean 0600 auth.json. Resume then refused by the
   controller's terminal-planning-failure seal (by design) → FRESH campaign (0 science at risk).
2. Fresh campaign (ak-088dcb66) reached 7 iterations — all typed refusals/revises (0 science):
   q5-preauthored screen_refused **"C6 Ghost Replay driver must be a stable regular non-symlink
   file"** (REAL deployment gap: the closure ships only kernel_rnd/autokernel/**; the ghost replay
   files live in kernel_rnd/c6_mutants/), q4k screen refused (vec-dot protected surface —
   legitimate), rope screen refused (C6 unsupported operator — typed), 2 planner output refusals.
3. Fix `e691434a` on the descendant: vendor c6_mutants/run_falsification.py +
   results_20260821.jsonl into the execution closure. Config identity UNCHANGED (eac81e0d) →
   controller-level resume valid.
4. Supervisor runtime-root identity drift (dir stat) blocked a same-root relaunch (by design) →
   fresh runtime root + carried controller state (the established pattern). Stale tmux session
   from the crashed campaign blocked the launch → killed by exact session name.
5. **Campaign LIVE** (session ak-db6b1d57): carried 7 iterations, next=8, in-flight operation
   ae0aea2b8d building; science 0/10. Watcher journaling continuously.
