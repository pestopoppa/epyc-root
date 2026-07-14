# Orchestration Robustness Audit — why fixes don't stick

**Status**: DELIVERED — operator review + decision points below
**Created**: 2026-07-11
**Author**: Fable 5 orchestrating session (operator-directed: "persistent bugs regress almost immediately after fixing… investigate deeply, review/audit all bug fixes/logs/progress reports, assess weaknesses and how they should be fixed")
**Method**: 4 parallel investigation streams, 20 subagents (10 corpus extractors over `progress/2026-04..07` (152 files), git forensics, handoff mining, state-source enumeration, dashboard dataflow map, test-history forensics; panel-trio fix→break chain reconstruction; speed-drop forensics; GEPA/Pareto stagnation forensics), followed by a **6-skeptic adversarial verification pass + completeness critic**. Verdicts below are post-verification; falsified sub-claims are marked. Numbers labeled *[audit-extracted]* come from this audit's own corpus extraction, not from any pre-existing in-repo catalog.
**Related**: [loops-and-dashboards-audit-2026-07-05.md](loops-and-dashboards-audit-2026-07-05.md) (the standing loop audit — this document confirms its headline verdict and re-sequences its remediation), [autopilot-continuous-optimization.md](autopilot-continuous-optimization.md), [model-stack-single-source-update-pipeline.md](model-stack-single-source-update-pipeline.md) (the existing SSoT workstream this audit says to *finish, not reinvent*).

---

## Executive summary

**Root cause, one sentence: the system has no reliable way of knowing what it is actually running.** Configuration, code version, instrument health, and live dispatch state are each represented in multiple places that can silently disagree — and every recurring failure the operator experiences (dashboard whack-a-mole, dead promotion gate, phantom speed drops, fixes that regress "immediately") is some pair of those representations diverging. The June Fable5 review said it first: *"A system that cannot prove what is running cannot cure itself."* This audit substantiates that across ~250 extracted infra bugs, ~730 dashboard/autopilot commits, and 1,300+ autopilot trials, and converts it into a consequence-ranked remediation plan.

Quantified damage *[audit-extracted]*:
- **~251 orchestration-infra bugs** in the Apr–Jul progress record; **~28% are explicit re-fixes** of previously-fixed issues, rising 25%→~32% (Apr→Jul); July's extractor judged ~2/3 of July infra work regression re-fixing.
- **41% of all epyc-orchestrator commits** since May 1 land in just the dashboard+autopilot surfaces. `orchestrator_stack.py`: 55 commits, 6,560 lines churned, **net −292** — the same lifecycle logic rewritten repeatedly.
- **4462 REPL execution errors** per tap log rotation: 1262 `_final()` keyword arg crashes (models emit `FINAL(result=…)`, function only accepts positional), 403 unknown tool calls, 359 `ZeroDivisionError`. These silently terminate trials with tool errors rather than capturing the model's answer — quantified trial waste that compounds the unreachable promotion gate.
- Panel-trio (regions-lock/live-tap/topology): **9 fix waves, ~70 consistency commits**, fix→break latencies from hours to 46 days.
- Autopilot: **zero (or at most one) baseline promotion in its entire journal history**; last real frontier admission 304+ trials ago; ~60% of the last 500 trials dispatched candidates into a promotion gate that is unreachable by construction.
- "Deployed-but-not-live" (`code_stale` / stale-daemon) mentions: **2 (May) → 10 (Jun) → 76 (Jul)** — a 7× jump; fixes are being counted as landed while production runs old code.
- The **highest consequence-per-bug event fits none of the visible categories**: the autopilot died silently at trial 1302 (Jul 8, no crash message, no lock, no PID) and stayed dead ~23h with every dashboard reporting "active".

**The whack-a-mole mechanism (operator's panel-trio complaint), verified:** the three panels are join views over **eight sources with incompatible timescales** (kernel-instant `/proc/locks`; a ~1MB tail of a 512MB-rotating tap file = seconds of history; 2Hz `/slots` polls that lost identity fields at the v6 cutover; quasi-static config with divergent defaults). Reconciliation logic is **duplicated in three places** (client JS, per-endpoint enrichers, snapshot builder). Every fix picks an authority ordering for one panel pair, which changes what the third panel's join observes — the moles are conserved. The history shows a fuse↔decouple pendulum (Jun-28 fused failure domains → Jul-05 decoupled via TTL caches, forking freshness → Jul-06 re-fused into the coherent snapshot, ~20 commits + 2 same-day regressions). **Caveat from verification:** the coherent-snapshot work *did* cut dashboard churn ~5–10× after Jul-06 — server-side reconciliation works; it's simply unfinished, and the remaining client-side joins keep re-opening it.

---

## The weakness model (post-verification)

Verdict key: each was attacked by a dedicated skeptic; ✂ marks sub-claims falsified and removed.

### W1 — Config duplication with divergent defaults *(confirmed; "dominant" downgraded)*
Same fact independently resolved in 2–15 places with different hardcoded defaults: `ORCHESTRATOR_STACK_NUMA_MODE` (4 files/8 refs, **no writer anywhere**, false "launcher exports it" docstring; post-0c7218b5 the dashboard family defaults `both` while the config-compiler family still defaults `full`); `ORCHESTRATOR_PER_REGION_LOCKS` (10 files); role→port (5 authorities); tmp-dir (**two different env var names**); tap paths (~15 hardcoded copies, no shared constant); `paths` fallback silently redirecting to the **archived monorepo path** on config-load failure.
**Skeptic corrections:** not proven the *dominant* class (the standing audit's yield/gate diagnosis competes); the remediation is **not new** — it is the existing N11 / model-stack-single-source-update-pipeline strategy, still PARTIAL after a month, and the real cost is per-reader fail-closed migration, not artifact authoring. Direct precedent that compiled artifacts drift **when committed**: `derived/stack_priors.yaml` broke the template↔prior parity invariant on clean HEAD. A naive fail-loud flip broke ~8 config tests when actually attempted (2026-07-11).
**Fix (R1′):** finish/extend the existing SSoT pipeline to runtime facts (mode, behavior flags, ports, paths, instrument versions) as ONE launcher-regenerated manifest — **never git-committed, refreshed on full spawn AND API/daemon reload**; readers fail closed only after a manifest fixture is threaded through tests and ownership is defined for every entrypoint.

### W2 — Ephemeral behavior gates *(directionally real; core evidence corrected)*
✂ *Falsified:* "launcher sets PER_REGION_LOCKS only into the llama-server child env" — wrong; `orchestrator_stack.py:1529` sets it in the **API** env, the live API carries the full gate block, and `reload orchestrator` → `start_orchestrator` **is** a working replay owner (this class was already hit and fixed twice: J6 placement flags, tool sentinels).
**Real residual hazard:** any restart that **bypasses** the sanctioned entrypoints (raw `uvicorn`, bare `autopilot.py start`, a watcher) silently reverts gates to consumers' `'0'` defaults; `start_fable_authority_daemon.py` exists precisely because the bare path looked healthy while dropping authority state.
**Fix:** enforce single sanctioned entrypoints (bypass = loud), and add **startup attestation**: every process logs its effective gate-set + config hash at boot; dashboard renders and diffs them. A persisted store adds provenance but is optional; if adopted, own the "store-write is a no-op on a running process" drift explicitly.

### W3 — Observability derives what it should be served *(diagnosis fully confirmed; remediation redesigned)*
8 client-side cross-feed derivations, 10 bounded-tail file dependencies, **15 distinct coherence bandages** (the bandage inventory is itself the proof), two renderers for the same grid, identity correlation across two PID spaces, regex label parsing as correlation keys.
**Skeptic's viable design (replaces my original):** the uvicorn worker that dispatches a request already holds the region flock — have it **write a small JSON payload into the existing lock file under that flock** (pid, request_id, role, instance_idx, started_at). The dashboard already globs those files; this kills the PID-space correlation, the regex parsing, and the off-window recovery for the lock panel, and ties displayed state to lock lifetime (the timescale mismatch dies at the root). **Do not** demote tap files to pure audit logs (light/backend-managed-lock requests never take a region lock — tap remains authoritative for them + for content); keep the tap and lock panels *decoupled* rather than re-joined. Known accepted blind spot: direct-to-llama bench traffic (runs autopilot-paused). Migration is incremental — finish collapsing to the display-matrix renderer and delete the legacy JS path; **not** a 7k-line rewrite.

### W4 — Tests ratchet snapshots, not invariants *(core confirmed; gap statement narrowed)*
The flagship bug's defending assertions were **born in the same commit as the bug** (e94ef7a1, 2026-07-06) and defended it for 5 days until 0c7218b5 — and it was *reviewable as wrong at the time* (quarter servers demonstrably running on Jul 3 and Jul 6). ~230 string-presence asserts are the only guard on 7,022 lines of browser JS.
✂ *Falsified:* "no reload-survival / no live-process integration test" — `tests/integration/test_dashboard_restart_recovery.py` (SIGKILL chaos test, e59bfa25) exists. The genuine gap is narrower: **no dashboard-vs-running-stack parity test**, and **no CI or pre-commit gate exists in either repo** — any test policy currently relies on manual discipline.
**Fix (R3′):** (a) hermetic invariant test — `expected_stack_services(mode)` must cover every `NUMA_CONFIG` instance for that mode (this exact test fails under e94ef7a1's assertions); (b) operational read-only parity smoke (listening ports vs rendered payload) run in quiet windows; (c) reader-agreement contract tests for every multiply-resolved value; (d) *replace* — don't delete — string-presence JS tests; (e) wire enforcement through `epyc-root` hooks since no CI exists.

### W5 — Evidence plane: unreachable gate + unattested instruments *(outcome confirmed; mechanism corrected)*
✂ *Corrected mechanism:* the binding constraint is **not alpha-wealth exhaustion** (that block sits behind `if not seq.get("confirmed")` and only fires for new fingerprints — it is currently shadowed dead code). The binding gate is the **era-blind rate axis**: `confirmed` requires `E_quality≥20 AND E_rate≥20` (`safety_gate.py:789-810`), and `E_rate` caps at ~1.11 because the baseline window spans the concurrency 3→1 regime change — so `combined_E = min(...)` can never reach 20, let alone the 100 promotion floor. Alpha-wealth (genuinely 4.75× overspent) becomes binding only *after* the rate axis is fixed — remediation order matters.
Confirmed: the `tool_use` axis returned 0.0 for trials ~506–1302; its verdicts fossilized into **TTL-less blacklist entries** (`architect_delegation` t655, `specialist_routing` t664/t864) that still fence the operator's named levers and were *not* purged by the Jul-11 sentinel fix (✂ t1064 escalation removed from this list — that was a critic-rejection, not instrument fossilization). Blacklist TTLs already exist for post-1194 entries — the fix is a **backfill + era-fenced purge**, not a new mechanism. Contamination survives rewind (manual StrategyStore belief scrub still needed on Jul-11 despite fix 10a9596d).
**Fix:** (i) loop-side **gate-reachability preflight** modeling the E_rate ceiling (an alpha-only check would not stop the burn), exempting trials with promotion-independent value (seed_batch, baseline draws, deep_eval); (ii) **instrument attestation** — an eval axis must pass a known-good/known-bad control pair before its scores accrue evidence or feed blacklists (this is the audit's P3 canary, generalized); (iii) era-fenced blacklist purge now. Gate-semantics changes remain operator-signed per MEASUREMENT.md.

### W6 — Process amplifiers *(re-ranked by evidence)*
✂ *Demoted:* monolith **size** (the 2026-05 split relocated stable logic; `dashboard.py`, itself born at that split, stayed the hottest surface; extracted modules have near-zero fix density but `snapshot`/`tasks` fix-*rates* exceed `dashboard.py`'s — churn tracks requirement volatility, not line count). ✂ *Demoted:* parallel-session collisions (**<1%** of fix commits — 2/550; the vivid ride-along anecdote inflated a minor cause).
**Promoted ranking:** (a) **half-done migrations to multiply-read values** — PRIMARY (the parity break, the both-mode split, the W8 report-vs-selector drift fixed 7× in July); (b) **shipping new components straight into the live loop** (local planner: 15 harden/repair commits in <24h — iteration is normal; the defect is no shadow lane); (c) governance bloat, now measured **worse than the standing audit recorded**: 378-line master index, 389 handoffs, 669 open checkboxes.
**Fix:** migration-discipline rule (a change to any multiply-read value must enumerate + update ALL readers in one change; gitnexus impact + epyc-root hooks as enforcement); shadow lane before live loop; adopt the standing audit's governance fixes rather than re-deriving them.

### W7 — Deployed-but-not-live *(NEW — completeness critic)*
A fix that requires a restart that never happens: tested-green code inert while the stale daemon regresses. `code_stale`-class mentions grew 2→10→76 (May→Jul). This silently **inflates the apparent fix rate** and compounds W4: a green suite and a regressing production process coexist by construction.
**Fix:** "landed" is redefined as **live** — PID-age-verified restart is part of the fix's definition of done; extend the existing `--require-current-code` machinery from advisory to gating.

### W8 — No process supervision / crash-cause attribution *(NEW — highest consequence-per-bug)*
The 23-hour silent death (trial 1302 → 1305) had no watchdog, no death-cause ledger, and every dashboard said "active". Preceded by repeated reload failures and auto-pauses that also went unattributed.
**Fix:** supervisor + heartbeat + death-cause ledger for the loop; treat as a Phase-0 peer of "pause/run" decisions.

### W9 — Host-ops as a standing measurement confound *(NEW)*
Page-cache collapse (131GB free → chased as a `--membind` regression), concurrent-download poisoning, post-`drop_caches` NUMA pinning, CPU freq never journaled. Ties directly to the operator's "speed drops" report — see verdicts below.
**Fix:** journal per-timing-event covariates: `min_core_mhz`, `host_inflight`, `numa_balancing`, cache-warm state; filter speed analytics to ≥128-token generations.

### W10 — REPL execution layer bugs waste trials *(NEW — concrete, measured, quick-fixable)*
Full REPL error taxonomy extracted from `repl_tap.log` (4462 errors, 4280 `CALL()` invocations vs only 93 `TOOL()` — models overwhelmingly emit `CALL()`). Three bugs silently waste trials at high volume:
- **`_final()` signature mismatch (1262 errors):** `context.py:169` declares `def _final(self, answer: str)` (positional-only). Models emit `FINAL(result=…)` (760) and `FINAL(secret=…)` (502). The TypeError terminates the trial with a tool error — the answer exists but the framework can't capture it. Source: `environment.py:418` maps `FINAL → self._final`.
- **Unknown tools (403 errors):** `get_eval_secret` (213) is gated by `AUTOPILOT_TOOL_SENTINELS=1` in `builtin_tools.py:40` — when off, the tool isn't registered but prompts still reference it. `search_files` (154), `get_time` (72), `fetch_stock_price` (34), `web_research` (16), `translate_text` (16), `start_service` (16) have no implementation in either the tool registry or REPL globals. Dispatch at `context.py:529-544` falls through `tool_registry.invoke()` → `ValueError` → `_globals` fallback → not found → propagates.
- **`ZeroDivisionError` (359 errors):** Models generate code that divides by zero. Not a framework bug — models need better numeric safety in generated code.
- **StrategyStore index degradation:** `sqlite=1424, faiss=1424 (99.9%), fts=1423 (99.9%)` — minor, 1 missing each in FAISS/FTS vs SQLite.
- **Trial 1304 killed mid-trial:** `autopilot_killed_mid_trial` — possible resource/stall issue (one instance).
**Fix (quick wins, hours):** (a) `_final()` accepts `**kwargs` and normalizes `result`/`secret` → `answer`; (b) either implement missing tools as stubs (returning descriptive "not available" responses) or remove their references from prompts so models don't call them; (c) confirm `AUTOPILOT_TOOL_SENTINELS=1` is set in all eval-bearing REPL sessions.

### Dominant interactions (worse than any single class)
- **W5×W1:** era-blind instrument × multi-site rule resolution ⇒ blacklists nobody can trust or attribute — this pair, not either alone, killed the promotion pipeline.
- **W7×W4:** stale daemon × snapshot tests ⇒ green tests + regressing production, by construction.
- **W8×W6:** unsupervised loop × turn-driven observation ⇒ 23h dead, unnoticed.
- **W10×W5:** REPL execution bugs × unreachable gate ⇒ 1262+ answers silently dropped per log rotation, compounding the already-unreachable promotion gate with noise that masks genuine improvement signals.

---

## Operator-reported symptoms — closed verdicts

**"Token speeds suddenly drop":** host is healthy (4.1–4.5GHz under load, `numa_balancing=0`, no PSI stall, no swap traffic; drop_caches/pinning ruled out in-window). ~90% of apparent drops are **measurement artifacts**: 1-token generations (fixed overhead ÷ 1 token), `speed_metric_mode` flips (aggregate vs median are incomparable), conc=1 vs conc=3 alternation (~37 vs ~10 t/s by design), eval routing-mix shifts, failed evals. Filtered to ≥128-token generations, every (role, shape) is steady across the window (worker_general.full 44–45 t/s; frontdoor.half0 ~32). Genuinely-felt slowdowns = interactive requests colliding with eval bursts (real, by-design; 40.5→11.9 t/s on 2-way overlap). Historic transient throttle is unfalsifiable because frequency is not journaled → W9 instrumentation. Note the `speed_metric_mode` trap was documented in the June Fable5 review and still poisons interpretation — a known-issue recurrence.

**"GEPA+Pareto stagnant for hundreds of trials":** structural, and predicted by the Jul-05 audit. None of the P2/P3 unblockers landed; the rate-axis ceiling makes `confirmed` unreachable; zero-or-one promotions in journal history; last real frontier admission 304+ trials ago; the rebuilt Pareto archive is empty (journal-recorded admissions don't survive the rebuild filter — itself a W1-class dual-view bug). GEPA specifically: 27% of species budget, **0 completed evals in 500 trials** (frontdoor prompt frozen under a "remove after restart" blacklist entry since Jun-05). The operator's "tool use and delegation never tweaked" intuition is **verified** — those levers are absent from the numeric catalogue, or fenced by blacklist entries earned while the tool_use axis was returning 0.0. **Concrete trial evidence (Jul-11):** trials 1300–1309 all dominated, mostly by `seq_accumulating` or `seq_stale_reference`; current trial 1310 just dispatched a `prompt_mutation` on `frontdoor.md` (appropriate pivot away from exhausted `numeric_trial` surfaces). Pareto frontier has only 5 points with tiny gap between q=2.040 and q=2.100. No inference/API errors in recent logs — stagnation is genuine search exhaustion, not infrastructure failure.

---

## Remediation plan (consequence-ranked; dashboard cosmetics LAST)

**P0 — operator decisions (this week, mostly sign-offs):**
1. **Run/pause call on autopilot.** It is currently burning ~16min eval-wall + planner spend per candidate trial into an unreachable gate. Either pause candidate species until P0.2 lands, or accept the burn knowingly, or land the loop-side reachability preflight (W5-i) which keeps seed/baseline/deep_eval running.
2. **Sign the P2 amendment bundle — rate-axis era-fence FIRST** (it is the binding constraint; alpha re-price is secondary), power calibration, frozen null + the P3 positive-control canary. **Gate the bundle on the eval-discriminability audit** (promoted per the completeness critic — a saturated suite invalidates every calibrated threshold).
3. **Authorize the era-fenced blacklist purge** (t655/t664/t864 + frontdoor GEPA freeze) and re-open tool-use/delegation levers under the repaired axis.

**P1 — highest consequence-per-bug engineering (~days):**
4. **Loop supervision (W8):** supervisor + heartbeat + death-cause ledger.
5. **Deploy gap (W7):** PID-age-verified "landed"; `--require-current-code` becomes gating.
6. **Startup attestation (W2/W1):** every process logs effective gate-set + config hash; dashboard diffs them; bypassing sanctioned entrypoints becomes loud.
6a. **REPL `_final()` keyword arg fix (W10):** accept `**kwargs` on `_final()` and normalize `result`/`secret` → `answer`; eliminates 1262 TypeErrors per log rotation that silently waste trials with captured-but-undelivered answers.
6b. **Unknown tool cleanup (W10):** implement missing tools (`search_files`, `get_time`, etc.) as descriptive stubs or remove from prompts; confirm `AUTOPILOT_TOOL_SENTINELS=1` in all eval-bearing REPL sessions; eliminates 403 `ValueError: Unknown tool` errors per log rotation.

**P2 — structural (~1–2 weeks):**
7. **Finish the SSoT pipeline (R1′):** extend N11 to runtime facts; launcher-regenerated (never committed) manifest refreshed on spawn AND reload; per-reader fail-closed migration with test fixtures.
8. **Lock-file payload enrichment (R2′):** JSON under the already-held flock; collapse to the display-matrix renderer; tap stays authoritative for non-lock requests; panels stay decoupled.
9. **Host/eval covariates (W9):** journal `min_core_mhz`/`host_inflight`/`numa_balancing` per timing event; ≥128-token analytics filter.

**P3 — policy (ongoing):**
10. Migration-discipline rule enforced via gitnexus impact + epyc-root hooks (no CI exists — hooks are the only enforcement point).
11. Invariant-first tests: the hermetic NUMA-parity test, reader-agreement contracts, operational read-only smoke.
12. Shadow lane for new components before the live loop.
13. Measure the right things: **regressions-per-active-trial and promotions-per-100-trials**, not commit volume (the July commit-rate decline was a loop-outage artifact, not convergence — the "system is converging" reading is falsified).

**Explicit de-prioritizations:** stop the dashboard cosmetic fix waves (streetlight bias — consequences ranking: launcher/lifecycle > eval instrument > checkpoint-rewind ≫ dashboard); do not split monoliths for size; do not delete string-presence JS tests until replacements exist; do not re-derive governance fixes the standing audit already wrote.

---

## Honest notes
- Two of this week's fixes by this session (43578845 off-tap recovery, 0c7218b5 region-locks grid) are correct locally but are themselves **W1-pattern spot-fixes**: 0c7218b5 aligned the dashboard family's default (`both`) while the config-compiler family still defaults `full` — the divergence persists one layer down. Even careful root-caused fixes inside this architecture reproduce the disease; that is the strongest argument for R1′.
- Two claims relayed to the operator mid-audit were corrected by verification and are retracted above: the alpha-wealth-as-binding-gate mechanism (real arithmetic, non-binding — the rate axis binds) and the PER_REGION_LOCKS reload-reversion mechanism (launcher does replay it on the sanctioned path; hazard is bypass-only).
- Promotion count discrepancy: journal key-scan found 0 `baseline_promotion` rows; the completeness critic counted 1 across 1169+ trials. Effectively none; not material to any conclusion.
- **W10 evidence source (Jul-11):** REPL error taxonomy extracted from `repl_tap.log` by this session — 4462 errors, 10 categories. The `_final()` keyword mismatch and unknown tool counts are verified by grep across the tap, not inferred. Model output pattern (4280 `CALL()` vs 93 `TOOL()`) is a confirmed emission bias — extraction handles both paths but it suggests the system prompt may need tuning toward `CALL()` as the preferred form.

## Checkpoint completions — 2026-07-11
- [x] Autopilot sequential gate preflight now defers promotion-dependent candidate actions when rate-axis reachability is impossible or alpha wealth is exhausted, and pivots to baseline/reference draws ✅ 2026-07-11
- [x] Builtin compatibility tools now register `search_files`, `get_time`, `fetch_stock_price`, `translate_text`, `start_service` with safe/read-only behavior ✅ 2026-07-11
- [x] REPL `FINAL(...)` now accepts `answer`/`result`/`secret`/`value`/`response` aliases and rejects unsupported kwargs with a clear `ValueError` ✅ 2026-07-11
- [x] Autopilot supervisor/death ledger wrapper landed (`autopilot_supervisor.py`, `start_fable_authority_daemon.py` bounded restart/death-ledger defaults) ✅ 2026-07-11
- [x] Startup attestation landed (config digests, combined config hash, gate env capture, mismatch reporting, phase health display of tool/planner flags, including visible planner spend-breaker state) ✅ 2026-07-11
- [x] Planner spend-breaker hardening stayed opt-in for local planner runs: the coordinator default is now off when the env is absent, the authority daemon still pins `AUTOPILOT_PLANNER_SPEND_BREAKER=0`, and the live restart confirmed that env at `0` ✅ 2026-07-11
- [x] PID-age-verified preflight gate landed: `start_fable_authority_daemon.py --preflight` now exits nonzero unless the live PID is age-verified current; the live rejection on Dirac's MH-9 worker is expected because unreviewed runtime `controller_io.py` edits predate PID `1039446` ✅ 2026-07-11
- [x] Host timing covariates landed for P2.9: `host_health.py` now records `min_core_mhz`, `host_inflight`, `numa_balancing`, and cache/cache-memory state; `eval_tower.py` captures compact per-question host covariates plus `tokens_generated` and adds observe-only >=128-token speed analytics fields in `EvalResult.details` ✅ 2026-07-11

## Checkpoint completions — 2026-07-14
- [x] W2 direct AutoPilot start bypass now fails closed in `epyc-orchestrator` commit `fc0be9bc`: `scripts/autopilot/autopilot.py start` exits `2` before taking the singleton lock when authority env is missing/mismatched, points operators to `scripts/autopilot/start_fable_authority_daemon.py`, and requires `AUTOPILOT_PLANNER_SPEND_BREAKER=0` rather than turning the spend breaker on. ✅ 2026-07-14
- [x] W8/Fable quiet-window evidence refreshed in `epyc-orchestrator` commit `5876a473`: `orchestration/reports/fable5_gate_report_20260714T111641Z.{json,md}` and `w8_promotion_trajectory_20260714T111641Z.{json,md}` confirm AutoPilot is stopped, W8 replay concentration is not warning, W4/W6 restart cutover is still blocked by the W6 gaming alarm, and the tool-use sentinel lane is ready but requires controlled API reload plus authority-daemon restart. ✅ 2026-07-14
- [x] HALO quiet-window spike closed as `completed-not-actionable`: operator-approved install succeeded, 3,532 spans were converted, the HALO canonical compatibility transform validated in `/tmp`, and the analyzer run failed before inference because local `/v1/responses` returned 404; outcome doc is `research/deep-dives/halo-spike-results-2026-07-14.md`. ✅ 2026-07-14
- [x] Controlled API reload plus authority-daemon recycle completed for the tool-sentinel lane: stale supervisor/child `1816107`/`1816109` were SIGTERM/SIGKILL verified dead, fresh supervisor `1890099` with child `1890100` resumed on `AUTOPILOT_TOOL_SENTINELS=1` and gate-3 profile, and the phase advanced to `planner_prompt_build` with `code_stale=false`, `tool_sentinels=true`, `w6_audit=true`, and `AUTOPILOT_PLANNER_SPEND_BREAKER=0`. ✅ 2026-07-14
- [x] Gate-3 latest verification hard-passed against orchestrator PID `1885933`: `get_eval_secret` returned `7/7` success rows, no-tool isolation passed, soft `WEB_RESEARCH: INFRA_FAIL` now fails closed as `web_research result failed (search_failed)`, and a forced web probe after reload still returned a relevant Python.org result through DDG fallback while preserving `success:true`. ✅ 2026-07-14

## Tasks
- [ ] P0.1 operator run/pause decision on autopilot candidate species
- [ ] P0.2 P2 amendment bundle signed (rate-axis era-fence first) + discriminability gate + P3 canary
  - [x] W5 control-pair attestation report-only scaffold landed in `epyc-orchestrator` commit `7a2a7c89`: `hle_metrics.py` now journals default-off `oracle_adequacy.control_attestation` status (`disabled`/`no_controls`/`incomplete`/`failed`/`passed`) from supplied known-good/known-bad rows without changing SafetyGate, Pareto admission, learning exclusion, blacklists, or thresholds. Binding gate remains operator/policy-gated. ✅ 2026-07-11
  - [x] P0.2a report-only amendment evidence view landed in `epyc-orchestrator` commit `65d4cf40`: `fable5_gate_report.py` now surfaces rate-axis state, latest oracle control-pair attestation, eval discriminability/T3 hard-lane coverage, and RI-10 canary state under `p0_2_amendment_bundle_inputs` with empty blockers and explicit `operator_signing_required`; signed P2 amendment / binding rate-axis era-fence remains operator-gated. ✅ 2026-07-11
- [ ] P0.3 era-fenced blacklist purge + tool/delegation lever re-exploration
  - [x] P0.3a guarded purge planner/apply helper landed in `epyc-orchestrator` commit `a26e6c6a`; dry-run identified exactly the 5 audit-scoped entries (`frontdoor.md` prompt/GEPA freezes, t655, t664, t864) and preserves 49 others. Apply remains operator-gated by `--approval-token ERA_FENCED_BLACKLIST_PURGE_2026_07_11`. ✅ 2026-07-11
  - [x] P0.3b audit-scoped tool/delegation re-exploration landed in `epyc-orchestrator` commit `134ed346`: AutoPilot now marks the three automated instrument-era structural blacklist entries (`architect_delegation` t655, `specialist_routing` t664/t864) as retryable without rewriting YAML, preserves manual frontdoor prompt/GEPA freezes behind the approval token, and journals `p0_3_blacklist_reexploration_*` rationale when dispatching those retries. ✅ 2026-07-11

### P0 operator gate packet - prepared 2026-07-11

This packet is command-discovery and evidence packaging only. It does not authorize a running autonomous session to pause/resume AutoPilot, sign measurement-policy changes, rewrite the blacklist, or enable the planner spend breaker.

- **P0.1 run/pause call:** inspect current-code and gate status before deciding:
  - `cd /mnt/raid0/llm/epyc-orchestrator && python3 scripts/autopilot/start_fable_authority_daemon.py --preflight`
  - `cd /mnt/raid0/llm/epyc-orchestrator && python3 scripts/autopilot/autopilot_restart_advisor.py --json --strict`
  - `cd /mnt/raid0/llm/epyc-orchestrator && uv run --with pyyaml python scripts/autopilot/fable5_gate_report.py --json --require-current-code`
  - Decision boundary: keep candidate species running only as an explicit operator choice while the rate-axis/P2 amendment remains unsigned; otherwise pause candidate species or let the preflight/reachability deferral route only promotion-independent work.
- **P0.2 amendment bundle:** use the report-only evidence view, then sign outside AutoPilot:
  - `cd /mnt/raid0/llm/epyc-orchestrator && uv run --with pyyaml python scripts/autopilot/fable5_gate_report.py --json --out-json orchestration/reports/p0_2_amendment_bundle_inputs_20260711.json --out-md orchestration/reports/p0_2_amendment_bundle_inputs_20260711.md --require-current-code`
  - Inspect `p0_2_amendment_bundle_inputs`: rate-axis state, latest oracle control-pair attestation, eval discriminability / T3 hard-lane coverage, RI-10 canary state, and `operator_signing_required`.
  - Boundary: this report is non-binding. Any rate-axis era fence, calibration baseline, frozen null, threshold, or P3 canary adoption remains a MEASUREMENT.md human-amendment action.
- **P0.3 blacklist purge:** preview first, apply only with the explicit token:
  - Preview: `cd /mnt/raid0/llm/epyc-orchestrator && uv run --with pyyaml python scripts/autopilot/blacklist_purge_plan.py --print-md --report-json orchestration/reports/p0_3_blacklist_purge_plan_20260711.json --report-md orchestration/reports/p0_3_blacklist_purge_plan_20260711.md`
  - Apply, operator only: add `--apply --approval-token ERA_FENCED_BLACKLIST_PURGE_2026_07_11`.
  - Boundary: the automated re-exploration exception for t655/t664/t864 is already live without rewriting YAML; the destructive purge of manual frontdoor freezes stays gated.
- [x] P0.1 packet validation: `start_fable_authority_daemon.py --preflight` and `autopilot_restart_advisor.py --json --strict` both report AutoPilot PID `1039446` active on trial `1317`, `code_stale=true`, `restart_needed=true`, `safe_to_restart_now=false`, and `status=wait_for_boundary`; no pause/restart was performed. ✅ 2026-07-11
- [x] P0.1 report-action hardening landed in `epyc-orchestrator` commit `2b78c2f3`: `fable5_gate_report.py` now points the `recover_autopilot_phase` next action at `start_fable_authority_daemon.py --preflight` instead of the weaker phase-health-only report, with a regression test. ✅ 2026-07-11
- [x] P0.2 packet validation: the report-only amendment view ran to `/tmp`, with `p0_2_amendment_bundle_status=attention`, `rate_axis=below_required`, `control_attestation=missing`, `eval_discriminability=low_coverage`, `operator_signing_required=true`, and evidence gaps `rate_axis_below_required`, `control_attestation_missing`, `eval_discriminability_low_coverage`. ✅ 2026-07-11
- [x] P0.3 packet validation: dry-run purge preview still identifies `54` entries before, exactly `5` removable audit-scoped entries, and `49` preserved entries; destructive apply remains token-gated. ✅ 2026-07-11
- [x] P1.4 loop supervisor + death-cause ledger ✅ 2026-07-11
- [x] P1.5 PID-age-verified "landed" definition (`--require-current-code` gating) ✅ 2026-07-11
- [x] P1.6 startup attestation (gate-set + config hash logged and diffed) ✅ 2026-07-11
- [x] P1.6a REPL `_final()` keyword arg fix — accept `**kwargs`, normalize to `answer` (W10, 1262 wasted trials) ✅ 2026-07-11
- [x] P1.6b Unknown tool cleanup — stub or remove from prompts; confirm `AUTOPILOT_TOOL_SENTINELS=1` (W10, 403 wasted trials) ✅ 2026-07-11
- [x] P2.7 runtime manifest via existing SSoT pipeline (N11 extension) ✅ 2026-07-11
  - Runtime-only derived manifest now refreshes from stack lifecycle events and is kept out of git; the launcher writes `/mnt/raid0/llm/tmp/orchestrator_runtime_facts.json` on start/reload and best-effort after state save.
- [x] P2.8 lock-file JSON payload + display-matrix renderer collapse ✅ 2026-07-11
  - [x] P2.8a region-lock payload attribution landed in `epyc-orchestrator` commit `799f1655` ("Add region lock payload attribution") ✅ 2026-07-11
  - [x] P2.8b display-matrix renderer collapse landed in `epyc-orchestrator` commit `4de996ea` ("Collapse region lock grid onto display matrix") ✅ 2026-07-11
  - [x] P2.8c browser fallback removal landed in `epyc-orchestrator` commit `08e94997`: `dashboard.html` no longer reconstructs a region-lock grid from legacy `by_role`/PID data when the backend display matrix is unavailable; it shows an explicit diagnostic instead, so observability cannot silently fork lock authority again. ✅ 2026-07-11
- [x] P2.9 host covariates journaled per timing event ✅ 2026-07-11
- [ ] W1 runtime-facts consumption follow-up: remaining runtime-facts-backed reader consolidation stays open for surfaces beyond the validated stack-service slice; a live reader insertion for `/mnt/raid0/llm/tmp/orchestrator_runtime_facts.json` was prototyped and reverted after `gitnexus impact active_stack_numa_mode --repo epyc-orchestrator --direction upstream` returned HIGH risk (`22` upstream impacts across dashboard health/topology/node detail/snapshot/tap flows). Re-enter only with explicit acceptance of that blast radius; do not paper over this with another env/PID fallback.
  - [x] W1 runtime-facts stack-service slice landed in `epyc-orchestrator` commit `db62aa3f`: runtime facts manifest now records `runtime_stack.stack_numa_mode`, `selected_servers`, `selected_ports`, and effective paths; stack start/reload/stop refresh the manifest at persisted-state boundaries; dashboard `expected_stack_services()` uses validated runtime selected servers when no explicit `ORCHESTRATOR_STACK_NUMA_MODE` override exists, otherwise it falls back to static manifest behavior. ✅ 2026-07-14
- [x] P3.10 migration-discipline hook (all readers in one change) ✅ 2026-07-11
  - Root commit `6d023e9d` enforced stack-fact migration discipline with the pre-commit hook, validator, candidate gate integration, and focused tests; verified with `py_compile`, `bash -n`, targeted pytest, negative/positive CLI checks, and `git diff --check`.
- [x] P3.11 hermetic NUMA-parity invariant test + reader-agreement contracts ✅ 2026-07-11
  - Commit `608cc54c` landed the shared NUMA-mode normalization helper and aligned launcher, stack-priors, template, guard, and dashboard readers on the same contracts.
  - [x] P3.11a W4/W9 read-only topology parity smoke landed in `epyc-orchestrator` commit `8bbf3eb5`: `test_topology_parity_smoke_for_expected_listener_ports` verifies known-port scanning includes every expected `both` stack service, simulated discovered listeners render as running topology nodes, and undiscovered expected services remain represented as unloaded stack servers. ✅ 2026-07-11
  - Root-side durable record landed in `epyc-root` commit `269c19bb` (`Record topology parity smoke`). ✅ 2026-07-11
- [x] P3.13 regressions-per-active-trial + promotions-per-100-trials metrics ✅ 2026-07-11
  - Commit `fa0391a5` reported the active-trial outcome progress metrics in the phase-status/autopilot/dashboard path; verification stayed clean with Ruff, `py_compile`, the focused pytest batches, and `git diff --check`.
- [x] P3.12 shadow lane for new live-loop components ✅ 2026-07-11
  - Commit `d596b5b2` ("Gate live-loop dispatch on action availability") added the live-loop shadow lane: planner-selected dispatch now skips outside the active allowlist, while sequential/due/fresh-eval/baseline/candidate-replay paths keep their own policy gates.

*Index status: accepted by the operator-directed 2026-07-11 robustness implementation thread; discoverable from the master N2 row and the routing/autopilot dispatch row. Keep current runtime truth in `autopilot-continuous-optimization.md` + `phase_health_report.py --json`.*

## Checkpoint completions — 2026-07-14
- [x] W1 runtime-facts reader slice completed in `epyc-orchestrator` commit `db62aa3f`: the runtime-facts manifest now records `runtime_stack.stack_numa_mode`, `selected_servers`, `selected_ports`, and effective paths; stack start/reload/stop refresh the manifest at persisted-state boundaries; dashboard `expected_stack_services()` uses validated runtime selected servers when no explicit `ORCHESTRATOR_STACK_NUMA_MODE` override exists. ✅ 2026-07-14
- [x] AutoPilot seq-preflight/live-allowlist deadlock fix completed in `epyc-orchestrator` commit `39fc3653`: deferred seq-gate replacement now bypasses the ordinary planner-selected live-loop allowlist, so retryable `seed_batch` fallbacks can dispatch after the preflight chooses them instead of looping on an allowlist rejection. ✅ 2026-07-14

## Checkpoint completions — 2026-07-11

---

## Research Intake Interface — 2026-07-11 (external source; operator-review, NOT new tasks)

Research-intake **intake-798** ("The Gemma Challenge and the Case for Agent Collabs", HF + Google DeepMind) processed a large open agent-collaboration that ran an autonomous propose→eval→gate→promote loop over the exact same problem shape as autopilot. Its published coordination/verification design ([`gemma-bucket-sync/DESIGN.md`](https://huggingface.co/spaces/gemma-challenge/gemma-bucket-sync/blob/main/DESIGN.md)) is a **worked reference implementation of several properties this audit says autopilot lacks** — offered here as external corroboration + concrete design precedent for the existing W-fixes, *not* as new work items (deliberately no checkboxes added — this audit already flags 669 open checkboxes as bloat). All external claims are attributed; none are imperatives.

- **↔ W5 (unreachable/unattested evidence plane) — tightest interface.** Their verifier fires **only when a claim strictly beats the current champion** (SOTA trigger), re-runs it against a **private held-out prompt set**, and admits only within a tolerance band (±5% TPS) *and* a quality gate (PPL ≤ 2.42). That is a clean, cheap, **gate-reachability-respecting** verification design — the shape W5-i (loop-side reachability preflight) and W5-ii (instrument attestation via a known-good/known-bad control) are reaching for. Crucially, their **automated negative verdicts stay `pending`/re-triable; only human verdicts persist forever and are never overwritten** — the opposite of autopilot's **TTL-less fossilized blacklists** (t655/t664/t864). Lesson for the era-fenced purge (P0.3): automated fences should default to expiring/`pending`, human verdicts to sticky — matching MEASUREMENT.md's human-amendment-only boundary.
- **↔ W1/W2/W3/W7 ("no reliable way of knowing what is running").** Their answer is **structural single-writer**: only the server writes the central store, it **server-stamps every path** (agents never construct central paths), and the read model is **write-through so read-after-write is exact, with TTL only to catch out-of-band edits**. This is precisely the coherent-snapshot direction W3 confirms works (~5–10× churn cut post-Jul-06) and the launcher-regenerated single manifest R1′ proposes — an adjacent-domain existence proof that the structural-constraint approach (not RBAC, not more reconciliation bandages) is the one that converges.
- **↔ W8 (no supervision; 23h silent death) + W7 (deployed-but-not-live).** They run an **in-process watcher** that polls, enforces a 40-min cap, and on completion writes `job_status.json`/`job_logs.txt`; quota state is a **durable ledger that survives restarts and fails closed** (unreadable ledger ⇒ refuse, don't spend). Their honest note — *watcher state is in-memory and lost on restart, but the job still completes and writes `summary.json`, so loss is bounded* — is the exact **"authoritative state durable, in-memory reconstructable"** principle W8's supervisor+death-cause-ledger needs. Their **`reconcile` pass heals results left `pending` by a Space restart** — the missing primitive behind autopilot's empty-rebuilt-Pareto bug (journal admissions not surviving the rebuild filter, a W1-class dual-view).
- **↔ GEPA/Pareto "genuine search exhaustion" (operator symptom).** intake-798's headline failure mode is **Agent Collapse** — the swarm converged onto a narrow set of axes and avoided the hard wins (custom quant, large kernels, engine changes), driven partly by **message-board "context rot"** self-reinforcing early topics. This is the *swarm analogue of autopilot's search exhaustion*; their proposed remedies (explicit exploration incentives, taskforces/channels to break the reinforcement loop) are candidate framings for the P0.3 lever re-exploration and any anti-monoculture proposal-sampling work in [`meta-harness-optimization.md`](meta-harness-optimization.md) (updated this session).
- **↔ W5 eval-gaming / discriminability gate (P0.2).** Their PPL-only gate **was gamed** (agents held PPL under threshold while degrading MMLU-Pro/GPQA by 15/40 pts); they reactively added MMLU-Pro + GPQA-Diamond for top submissions. Independent, real-world confirmation of the audit's "a single cheap proxy will be gamed; a saturated/1-D suite invalidates every calibrated threshold" concern — argues the discriminability audit gating P0.2 should treat **multi-dimensional + evolving** gates as the steady state, not a fix.

See also the gemma4-specific kernel spinoff: [`gemma-challenge-kernel-techniques-v7.md`](gemma-challenge-kernel-techniques-v7.md).

Related checkpoint: MH-9 new-file mutation support landed in orchestrator commit `88639b1f`, closing the PromptForge checkpoint without changing any remaining audit tasks.
