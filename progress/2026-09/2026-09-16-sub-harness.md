# 2026-09-16 — sub-harness: UFH-01 harness evidence + OP-9/FW-3 supervision package

All work was zero-inference. Nothing was started, stopped or killed. No host config was touched.

## 1. UFH-01 harness evidence (`handoffs/active/harness-selection-and-integration.md`)

- **HS-1g ✅ (call-verb check).**
  - Added the 4-step instrument to the Client Surface Audit in `hermes-outer-shell.md`.
  - Ran it on all five candidates, from source only. The clones are read-only, at
    `/mnt/raid0/llm/tmp/hs1g-{opencode,ohmypi,dsh,pi}`.
  - OpenCode, oh-my-pi and earendil-works/pi honour the body lever on every default path. For OpenCode this
    settles, at source, the HS-1c question of whether keys land top-level or nested: they land top-level.
  - **Hermes honours it on the main loop only.**
    - Compaction, the iteration-limit summary, `flush_memories` and `delegate_task` children all bypass
      the EPYC plugin's `extra_body`. Spot-checked: `context_compressor.py:346-355`,
      `delegate_tool.py:207`, `run_agent.py:845-852`.
    - So the HS-1b "≈0 patch" call needs `compression.enabled:false` plus a `delegate_task` gate.
  - **dsh** exposes no lever on its pi-ai route. Its native DeepSeek route has one. Its HEAD now pins
    pi-ai 0.85.1, which corrects HS-1e: the pin bump is already done upstream.
- **HS-13 ✅ (structured output).** The capability record is split into two layers and verified against
  `git show 0db32c06e:…`.
  - The kernel does grammar-constrained decoding through `json_schema_to_grammar`.
  - The `/v1` seam refuses `response_format` with a 422, by decision.
  - Native `/chat` REPL mode is parse-and-retry (and its flag is off by default).
  - **Kernel-doc defect:** the `README.md:1239` `json_schema` example is silently ignored by the code at
    `server-common.cpp:947-949`, which yields unconstrained JSON.
- **HS-6b ✅.** Re-read the card against HS-1e, HS-1f and HS-1g. One row was contradicted and is now
  corrected: Context assembly said harness compaction "can defer".
- **HS-6c ✅.** Published the conformant ETCSOVG card.
  - It uses the verbatim Table 3 fields from arXiv 2605.23950 and values from `epyc-orchestrator@92bbeb06`.
  - 13 fields are named as undisclosed or unfixed.
  - HARNESS_RUN_POLICY's "applicable Harness Card" requirement is now satisfiable.
- Not touched: HS-4 and HS-5 (operator decisions) and HS-1f.1 (needs inference).
- **Belief kernel:** added a README source-table row, plus task VB-HARNESS-AUDIT in
  `vidya-belief-substrate-program.md` (class decision: verifier / dependency-edge / decline).
- `cite-check` on the edited handoffs: clean.
- `index_state.py --check` fails only on "master index generated block is stale". The main session must
  regenerate it before committing.

### What the HS-4 packet now shows (no decision made)

| Candidate | Cooperation at source |
|---|---|
| OpenCode | Every default path honours the lever. One live confirmation is still owed. |
| oh-my-pi | Every default path honours the lever. |
| earendil-works/pi | Every default path honours the lever. Any extension must use the simple verbs. |
| Hermes | Main loop only. Needs config gating plus a small patch for the summary and memory-flush paths. |
| dsh | Needs a patch, or the native DeepSeek route. |

- Orthogonality and minimum-imports (HS-1f) still favour pi.
- The structured-output seam is closed by decision at `:8000`, not by the kernel.
- Any comparison on our tower is locked-harness only. The HS-6c gaps include no sandbox and auto-approve.

## 2. OP-9 + FW-3 supervision package

**Findings (read-only):**
- **fleet_watch.sh is dead.** Its last log line is 2026-08-18T12:54Z, which matches the container restart;
  the fleet has been unwatched for about 29 days.
- **The canonical hub_supervisor exited on 2026-09-14.** A replacement (pid 996612) was launched on
  2026-09-15 with `EPYC_ROOT` set to lane `worktrees/mains/autokernel-unified-20260908`.
  - The live hub (pid 2070612) therefore serves the lane.
  - Deploy-sync has written origin/main dashboard files into the lane's working tree since 09-10.
- **Every daemon runs inside the devcontainer `epyc-root`.** That container has a private `/tmp` and no cron.
  The only cron is the host's `cron.service`. So the 2026-08-24 cron line would run on the host, where it
  would not see the container's lock and would launch a host-side hub. That line is defective.

**Script fixes.** Branch `sub/harness-evidence-20260916`, commit `034dccbe`, worktree
`/mnt/raid0/llm/worktrees/sub-harness-epyc-root`, based on origin/main `b65138a0`. Not merged or pushed.
- `refuse_linked_worktree`:
  - It compares git `--git-dir` with `--git-common-dir`, which works in any namespace. The reverted
    `/proc` probe did not.
  - It exits 3 when `EPYC_ROOT` is a linked worktree. `HUB_ALLOW_LINKED_WORKTREE=1` overrides it.
- `check_hub_stale_source` no longer aborts the loop daemon under `set -e` when a restart fails.
- A restart now needs two failed `/health` probes (`hub_down_confirmed`).
- `once` now runs the same deploy-sync → stale-source sequence as `loop`.
- Tests:
  - new `scripts/dashboard/tests/test_hub_checkout_identity.sh`: 10/10;
  - `test_hub_stale_source.sh`: 5/5;
  - `test_hub_deploy_sync.sh`: PASS;
  - `tests/test_dashboard_panels*.py`: 147 passed.
- GitNexus does not index shell functions (impact returned "not found" / LOW, 0 impacted). I derived the
  blast radius by hand instead. The only external consumers are the two shell tests and the static checks
  in `tests/test_dashboard_panels.py`, and all of them pass.
- **Not deployed.** The running supervisor executes the lane copy. A relaunch is for the main session to
  schedule.

### OP-9 + FW-3 package (as filed in `handoff-index-and-backlog-graph.md`)

**Decision needed:** may we add supervision lines to the HOST crontab? This is host config, so it is
operator-only.

**Options**

| Option | What it is | Pros | Cons |
|---|---|---|---|
| **(a) — recommended** | Host crontab that enters the container with `docker exec` | One edit covers both daemons. Covers a single death **and** a container restart. About 1 s every 2 min. | Host change. Depends on the container name `epyc-root` and on docker group membership. |
| (b) | systemd user units running `docker exec … loop` | Restarts in seconds. Logs to the journal. | More host config (linger). Lifetime is tied to a foreground exec. |
| (c) | devcontainer `postStartCommand` | No host change. | Covers container restarts only. Needs a rebuild. `devcontainer.json` has another session's uncommitted edits. |
| (d) | Leave as-is | No change. | The observed cost continues: fleet_watch has been dead 29 days, and the hub serves a lane. |

**Recommendation: (a).** Install it only after `034dccbe` is merged and the supervisor has been relaunched
canonically.

```cron
# EPYC supervision tier (OP-9 / FW-3). Runs INSIDE the devcontainer; both targets are flock-idempotent.
*/2 * * * * docker exec -u node epyc-root /mnt/raid0/llm/epyc-root/scripts/dashboard/hub_supervisor.sh once >>/mnt/raid0/llm/epyc-root/logs/cron_supervision.log 2>&1
*/5 * * * * docker exec -d -u node -e PATH=/opt/rocm/bin:/usr/local/bin:/usr/bin:/bin epyc-root setsid -f /mnt/raid0/llm/epyc-root/scripts/coordination/fleet_watch.sh
# optional, rest of the tier:
*/2 * * * * docker exec -u node epyc-root /mnt/raid0/llm/epyc-root/scripts/coordination/bus_supervisor.sh once >>/mnt/raid0/llm/epyc-root/logs/cron_supervision.log 2>&1
```

**Sequence** (the main session schedules the process steps):
1. Merge `034dccbe`.
2. Coordinate with the owner of lane `autokernel-unified-20260908`.
3. Stop pid 996612.
4. Relaunch the supervisor canonically, with `EPYC_ROOT` unset.
5. Move the hub to the canonical root (`orchestrator_stack.py reload handoff_dashboard`).
6. Tell the lane owner which dashboard files deploy-sync wrote into their tree.
7. The operator installs the cron lines.
8. Verify both daemons:
   - `once` exits 0 with "another supervisor already holds";
   - a fresh "fleet_watch started" line appears.
9. Tick OP-9 and FW-3.

`fleet_watch.sh --once` is a diagnostic, not a restart primitive. The bare launch is the restart
primitive, and its lock in `logs/` makes a duplicate launch exit 3.

## 2026-09-16 rework: manifest is the source of truth

- **Premise corrected.** `034dccbe` treated "the hub serves a lane checkout" as a misconfiguration. It is
  intended: orchestrator `f5476148` (2026-09-09) sets `launch_manifest.yaml` `handoff_dashboard`
  cwd/pythonpath to `worktrees/mains/autokernel-unified-20260908`.
- **Commit `31d95ad8`** (branch `sub/harness-evidence-20260916`, worktree `/mnt/raid0/llm/worktrees/sub-harness-epyc-root`):
  - New `scripts/dashboard/hub_launch_spec.py` resolves the manifest entry with the orchestrator's own
    `_expand_paths` / `_aux_service` / `build_service_env`. `{python}` = the HUB_PYTHON interpreter.
    A local resolver with the same semantics is the fallback.
  - `start_hub` launches with the manifest cwd/env/argv. If the manifest is unreadable, it falls back
    loudly to cwd=EPYC_ROOT.
  - Home (EPYC_ROOT: logs, pids, state) is now separate from the hub source (manifest cwd). The
    stale-source check reads the hub source. Deploy-sync is skipped when the hub source is a linked
    worktree.
  - `refuse_linked_worktree` is replaced by `refuse_noncanonical_home`.
  - New read-only `plan` subcommand.
  - Kept: two-probe restart, once/loop parity, and no loop-daemon abort.
  - Marker: `HUB_SUPERVISOR_MANIFEST_LAUNCH_V1`.
- **Tests:**
  - `test_hub_manifest_launch.sh` 38/38. The fixture manifest points at a fake linked worktree; the
    test checks cwd/env/argv, no lane writes, and no refusal from the canonical home.
  - Deploy-sync (with a new lane-skip case) passes. Stale-source 6/6. Mutation checks were killed.
  - `test_dashboard_panels` + redteam: 147 passed.
  - The other 39 dashboard pytest failures are identical at `034dccbe`, so they pre-date this change.
- **Live drift found (read-only):** hub pid 2070612 runs `AUTOKERNEL_LOOP_STORE_ROOT=…aku-glm53-continuous-20260915-v12`,
  but the manifest says `…aku12a-glm53-five-loop-store`. Any manifest-driven relaunch switches store.
- **Preflight note:** `install_supervision_cron_20260916.sh --all` greps `linked worktree`, which still
  matches (the sync-skip text), so that grep is now vacuous. It should grep `HUB_SUPERVISOR_MANIFEST_LAUNCH_V1`.
