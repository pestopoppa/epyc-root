---
title: ESC-8 — Stack-script restart-landmine audit + Option A implementation contract
status: DEPLOYED 2026-07-22 — all six fixes + verification complete; landmine dead (see checklist)
created: 2026-07-22
owner: eval-tower-architecture-audit (ESC-8) / within-role-placement-state-machine (shared restart surface)
audit_agent: read-only; findings verified against live system + throwaway-interpreter imports
deploy_boundary: EV-11c terminal (single SIGSTOP → reload → SIGCONT batch with WP-13 regeneration + WP-14)
---

# Executive finding

**Production routes correctly today only by accident.** The live API (pid 1778291, started
2026-07-22 07:20:39 by `reload orchestrator`) carries `ORCHESTRATOR_STACK_NUMA_MODE=full`, and the
07:20:46 runtime-facts rewrite recorded a **structurally valid full-mode manifest**. The env-wins
branch of `src/config/models.py:_runtime_or_env_selected_servers` would wire every hot role to the
dead full ports (8070/8072/8085) — but in the uvicorn app-import path it dies on a circular import
(`src.api` → `scripts/server/stack_paths` module-level `get_config()` → `ServerURLsConfig` → back
into the still-initializing `stack_manifest` → `ImportError: cannot import name 'HOT_SERVERS'`),
is swallowed by `except Exception: return None` (models.py:339-340), and the config falls through
to stack-priors quarter URLs, which DISPATCH-A3 demotes correctly.

In any **plain-import** process with the same env (verified in the repo venv):
`get_config().server_urls` → frontdoor `:8070`, worker_general `:8072`, ingest `:8085`,
worker_fast `:8102` — **all dead**.

# Standing operator warnings (until the package deploys)

- ⚠️ **Do NOT run `scripts/registry/stack_change_pipeline.py update` from a clean shell** (kill
  chain A4): `compile_stack_priors` reads `env_stack_numa_mode()` (default **full**,
  `stack_numa_mode.py:10`) and would rewrite stack_priors.yaml to the full lineup — destroying the
  only correct fallback keeping the live API on quarters. Next API restart after that is a
  guaranteed dead-port outage.
- ⚠️ **No bare `start`, no `start --only <role>` without `--numa-mode quarter`** (A2/A3): default
  full would launch overlapping full instances next to live quarters and stamp `full` into the
  manifest. (The stack-change launch gate currently refuses bare `start` — by accident, via
  staleness — do not bypass with `--skip-stack-change-gate`.)
- ⚠️ Every `reload`/`stop` re-arms the poison (A1): they rewrite the facts manifest carrying
  `full` forward (stack_commands.py:1626, :1430, :1376 pass no mode).
- The 07:20:46 reload **upgraded the poison from inert to armed**: the previous invalid manifest
  ("stack_numa_mode None, selected_ports []") was fail-safe (readers rejected it → quarter
  priors); the current valid full-mode manifest is **accepted** by env-unset plain-import
  consumers and resolves to dead ports (verified empirically). D1 (env=full plain-import) and
  D2 (valid full manifest) are both armed now.

# 1. Env origin map — `ORCHESTRATOR_STACK_NUMA_MODE=full`

Only setter: `start_orchestrator` (`scripts/server/orchestrator_stack.py`):
- :1627 `env = os.environ.copy()` — full shell inheritance.
- :1630-1636 resolution: explicit `stack_numa_mode` arg → `read_runtime_stack_numa_mode()`
  (facts manifest, staleness-gated vs STATE_FILE) → inherited env; normalized and exported.

Per-caller behavior on a quarters-only deployment:
- **(a) `reload orchestrator`** — `stack_commands.py:1503-1505` passes
  `read_runtime_stack_numa_mode()`; today's manifest says `full` → env=full (exactly how the live
  API got it; manifest generated_at 07:20:46, source `stack_reload`). If the manifest is stale
  (e.g. after `status`, which `save_state()`s at :1711 *without* refreshing facts), the read
  returns None → falls to invoking shell env or unset. **Whether a reload arms env=full depends
  on whether someone ran `status` in between** (order-dependence hazard).
- **(b) full `start`** — `stack_commands.py:1050` default `"full"`; argparse default
  `orchestrator_stack.py:2099-2103`; `launch_production.sh` never passes `--numa-mode`.
- **(c) profiles** — no NUMA/URL vars; no effect.

Classification: **stale config read (facts manifest), self-perpetuating; ultimate origin =
hardcoded `full` defaults** (`DEFAULT_STACK_NUMA_MODE`, argparse default, writer's
normalize(None)→full). Timeline: v7 cutover day (07-20) started the full fleet 13:46:04Z,
quarters relaunched 13:54-13:56; "full" entered the manifest then and every reload since carried
it forward.

# 2. Runtime-facts writer defect

Writer: `write_runtime_facts_manifest` (`scripts/server/runtime_facts_manifest.py:173-199`) via
`_refresh_runtime_facts_manifest` (`stack_commands.py:314-336`). Call sites: cmd_start:1341
(passes mode), cmd_stop:1376/:1430 (**no mode**), cmd_reload:1626 (**no mode**).

1. **Mode**: with `stack_numa_mode=None`, :185-188 re-reads the previous manifest with staleness
   disabled; failing that, `_runtime_stack_summary` (:95-120) calls
   `normalize_stack_numa_mode(None)` → **"full"**. Unknown coerced to full, self-perpetuating.
2. **Lineup**: :101-104 derives `selected_servers`/`selected_ports` from the **static**
   `_filter_by_numa_mode(HOT_SERVERS + WARM_SERVERS, mode)` — never the realized fleet. Current
   file records ports 8070/8072/8085/8102/18070 while its own `state` block (same payload) lists
   the realized quarter fleet (8080/8082/8180/8182/8185/8280/8282/8285/8380/8382/8385/8485 — all
   pids verified alive, listeners quarters-only).

Correct serialization (sources available at write time): `selected_servers` from the realized
`state` argument (+ `topology_idx_for_port` from DISPATCH-A3, optionally cross-checked against
`discover_llama_markers`); `stack_numa_mode` derived from realized ports vs `NUMA_CONFIG`
full-instance ports (quarters-only ⇒ `"quarter"`); never default unknown to `"full"`.

# 3. Fix-survival matrix (this week's commits vs start/stop/reload)

| Fix (commit) | Survives restart? | Mechanism / what breaks it |
|---|---|---|
| DISPATCH-A/A2/A3 (99dd6c92, 570200ff, 5408109f) | Code yes; **engagement conditional** | Engages only when backends receive priors-style `full:8080,...` URLs — i.e. only because the env-wins branch crashes. Import-order change or plain-import consumer bypasses → dead ports. |
| worker_math URL + drift guard (89748805); Fix A delegation (830fa0ef) | Code yes | Resolve through `_server_url_default` → poisoned upstream by env=full (models.py:325-338) or the valid full manifest (:342-349). |
| Placement flags (PSM/REVERSE_MIGRATION/SHAPE_AWARE/PER_REGION_LOCKS/CROSS_ROLE) | **Yes** | `env.setdefault` durable defaults (orchestrator_stack.py:1648-1668); live env verified all `=1`. Shell env can deliberately override. |
| SERVER_URL env | N/A — safe | No script exports `*SERVER_URL*`; URLs computed in-process. |
| stack_priors.yaml | Not touched by start/stop/reload | Only `stack_change_pipeline.py update` rewrites it — and its compile reads default-full env (`stack_priors.py:777-779`) → A4. Launch gate on `cmd_start` (stack_commands.py:69-76, 191-222) accidentally blocks bare `start` today. |
| Take-down residue | Stop leaves stale artifacts | `stop --all` rewrites facts with `state={}` but poisoned mode; stale `llama_<port>_started_at` markers for dead ports never pruned (embedded in `facts.fleet_markers`); `cpu_region.*.lock` files persist (harmless). |
| Eval-cost tie-in | — | `eval_tower._live_safe_concurrency` (eval_tower.py:1056-1073) takes the quarter fan-out branch only when recorded mode is `"quarter"`; manifest saying `full` keeps eval concurrency conservatively capped. |

# 4. Kill chains

- **D1 (armed)**: plain-import consumer of `src.config` with env=full, or any refactor changing
  app import order → dead 8070/8072/8085. `reload orchestrator` re-arms env=full every run.
- **D2 (armed)**: env-unset consumers + valid full manifest → dead lineup (verified).
- **A1**: every reload/stop carries `full` forward.
- **A2**: `start --only <role>` default full → overlapping full instance + manifest stamp.
- **A3**: bare `start` / `launch_production.sh` → full-fleet launch (gate blocks by accident).
- **A4**: clean-shell `stack_change_pipeline.py update` → priors rewritten full → next restart is
  a guaranteed outage.

# 5. Option A implementation checklist (authorized; deploy at EV-11c terminal boundary)

- [x] ✅ 2026-07-22 (`1de3cef9`) **Fix 1 — facts writer realized-state serialization**: `runtime_facts_manifest.py:95-120`
  derive `runtime_stack` from realized `state` (+ `topology_idx_for_port`); `:103`/`:185-188`
  never coerce unknown mode to `"full"` — derive from realized ports. Liveness-filter dead state
  rows (8096-8098) and stale fleet markers.
- [x] ✅ 2026-07-22 (`1de3cef9` + cmd_start merge `5aa29f35`) **Fix 2 — pass realized mode at all writer call sites**: `stack_commands.py:1626, :1430,
  :1376`; `cmd_status` :1711 refresh facts after `save_state` (or stop saving state in status).
- [x] ✅ 2026-07-22 (`1de3cef9`) **Fix 3 — env alignment assertion**: `orchestrator_stack.py:1630-1636` after resolving
  `runtime_numa_mode`, assert against realized fleet (live listeners on NUMA_CONFIG full vs
  quarter ports); on mismatch correct to realized mode + log provenance.
- [x] ✅ 2026-07-22 (`1de3cef9`) **Fix 4 — kill hardcoded full defaults**: `orchestrator_stack.py:2099-2103` +
  `stack_commands.py:1050` `--numa-mode` default None → infer from running fleet; refuse
  `--only` on mode conflict.
- [x] ✅ 2026-07-22 (`5aa29f35`) **Fix 5 — config precedence inversion**: `models.py:316-349` validated runtime facts first,
  env-filter as fallback (or validate env lineup against live listeners); stop silently
  swallowing the ImportError — log it.
- [x] ✅ 2026-07-22 (`5aa29f35`; guard realized-mode `2ac7712c`/`d8b7e0bd`) **Fix 6 — priors compile must not read ambient default-full env**:
  `stack_priors.py:777-779` require explicit mode or read realized mode, so clean-shell
  `pipeline update` cannot rewrite priors to the full lineup. (Coordinate with WP-13 edits in the
  same file.)
- [x] ✅ 2026-07-22 (help text in `1de3cef9`; dashboard env-first fixed realized-first `e97d4ed9`; stack_templates default-full reader NOT yet hardened — folded into WP-12 scope) **Docs/consistency**: `--numa-mode` help text (orchestrator_stack.py:2103-2116) vs
  `stack_numa.py:173-184` FULL_DISABLED comment; `dashboard_topology.py:139-146` env-first
  display (WP-14 reader hardening covers); `stack_templates.py:257-259` default-full reader.
- [x] ✅ 2026-07-22 VERIFIED — plain-import clean-shell AND env=full both resolve quarter lineups (poison rejected loudly); manifest realized (mode quarter, 21 live servers); reload round-trips without re-arming; canonical env restored (quarter + all placement flags) **Verification at deploy**: post-reload, plain-import `get_config().server_urls` in a
  clean shell AND in an env=full shell both resolve to the quarter lineup; facts manifest
  records realized quarters + mode `"quarter"`; `reload orchestrator` round-trips without
  re-arming; DISPATCH-A3 demotion count unchanged.

# 6. Cross-references

- Authorization + decision record: `coordination/inference-batch/op-bundle.md` ESC-8 block.
- Durable replacement: `handoffs/active/wp12-fleet-layer-design.md` — makes env non-authoritative
  for fleet identity structurally (§2.1 construction: env not consulted); Fixes 1-6 are the
  interim that keeps the per-copy world safe until the fleet layer lands.
- Interim siblings landing at the same boundary: WP-13 (stack_priors alias-ports + convergence
  test), WP-14 (fail-closed manifest readers).


# 2026-07-25 — Cold-start follow-up (GEPA-validation session): 37-error class diagnosed + CLI threading fix landed

_Provenance: surfaced while validating the GEPA proposer fix (see [`intake-derived-work-2026-07-25.md`](intake-derived-work-2026-07-25.md) ID-1). Not registry drift — both registries committed-clean; gate was green at WP-13 (`d8b7e0bd`)._

**Diagnosis.** On a fully-cold host, `_launch_manifest_targets` (stack_change_guard.py:839) resolves the launch view as realized-fleet mode → env `ORCHESTRATOR_STACK_NUMA_MODE` → default `full`. Dead fleet ⇒ `derive_realized_numa_mode()` = None; clean shell ⇒ env unset ⇒ **launch view built for `full`** while the registry documents the restored `both` lineup ⇒ **37 wholesale errors** (same family as the 105-error class WP-13 fixed for live fleets). The CLI's explicit `--numa-mode both` was **never consulted by the guard**.

- [x] **Fix landed 2026-07-25**: `scripts/server/stack_commands.py` `_run_stack_change_launch_gate` now threads an EXPLICIT `--numa-mode` into the gate subprocess env (precedence preserved: realized > CLI > env > default; omitted flag unchanged). Validated: identical cold dry-run went **37 errors → 1** with the CLI flag alone; `tests/unit/test_orchestrator_stack_reload.py` 38/38 green. ✅ 2026-07-25
- [x] **Residual 1 error root-caused as BY DESIGN**: `_realized_compile_numa_mode` (src/registry/stack_priors.py) raises `StackPriorsModeError` whenever no realized signal exists — **even with env explicitly set** (its decision table only consults env when a fleet is listening). That is Fix 6 / kill-chain-A4 protection, so a gate-green cold start is currently impossible by construction. The `stack_paths`/`stack_manifest` circular-import warnings in gate output are the documented benign-by-accident landmine, NOT the cause. ✅ 2026-07-25
- [ ] **Cold-start recipe (until the design question below is settled)** — verified sequence:
  1. Pre-verify: `start --numa-mode both --dry-run` → confirm the ONLY remaining gate error is the `stack_priors` dead-fleet refusal (36 other checks green).
  2. Bring up: `start --numa-mode both --skip-stack-change-gate` — justified ONLY for cold bring-up after step 1's verification (the pre-deploy "do not bypass" warning targeted the since-closed A2/A3 hazards; benchmarks and autopilot resumes must still never bypass).
  3. Immediately after fleet-up: `scripts/registry/stack_change_pipeline.py update` — realized mode is now derivable, priors compile succeeds, gate debt cleared.
  4. Policy riders: stop autopilot before a full bring-up (SIGTERM + drain), restart after; per-run operator approval for llama-* remains in force.
- [x] **Design question RESOLVED 2026-07-25 — already decided, deliberately; no change warranted.** ✅
  I asked whether the GATE's stack_priors check should adopt a cold-fleet posture (trust an explicit
  CLI/env mode when no fleet is realized) instead of hard-failing. **The codebase already answers this,
  and the answer is no.** `tests/unit/test_stack_priors_compiler.py:1142` encodes the exact carve-out as a
  prohibited behavior, with the rationale in a comment: *"An explicit env does NOT rescue a no-signal probe
  (unverifiable fleet)."* Implementing the carve-out would require inverting a test that documents intent.
  - **Refined understanding of WHY the check path refuses** (this differs from the write path and I had it
    conflated): `_check_stack_priors` (`stack_change_pipeline.py:504`) sets `require_realized_mode=True` NOT
    for write-safety but for **comparison validity** — its own comment: *"so a clean-shell check computes the
    SAME lineup the update writes and cannot report the quarters-only priors as 'stale' against a full
    expected."* Kill-chain A4 protection lives only on the WRITE path (`:550`). Refusing is the fail-closed
    alternative to a comparison the tool cannot trust.
  - **Consequence for operators**: a gate-green cold start is impossible **by design**, not by defect. The
    cold-start recipe above (verify via dry-run that the ONLY residual error is the priors refusal, then
    `--skip-stack-change-gate` for bring-up, then `stack_change_pipeline.py update` immediately once the
    fleet is realized) is therefore the **sanctioned** path, not a workaround. The 36 other checks still run
    and must be green before the skip.
  - Anyone revisiting this must change the test and its comment first, with the owning surface's sign-off —
    that test is the specification.
