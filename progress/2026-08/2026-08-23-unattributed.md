# 2026-08-23 — opencode ad-hoc session (tier-1 non-inference backlog + RTG-35 re-measure + wrap-up)

**Agent**: opencode (ad-hoc, no lane; log shard `logs/agent_audit-unattributed.log`, session
`ses_20260823_091653_3747852`). Detailed entries also live in the shared
`progress/2026-08/2026-08-23.md` (committed). This shard is the self-contained close-out record.

## Mandate

Operator-requested: (1) overview of highest-ROI non-inference-gated backlog; (2) execute all Tier-1
items via parallel subagents; (3) execute the RTG-35 OP-21 overlap re-bench; (4) resolve residuals
(SS-BENCH-GATE-b, q_scorer test, matrix demotion + API reload, artifact-deletion matter); (5) wrap-up.

## Work delivered (all committed + pushed)

### epyc-orchestrator
- **RTG-35** — `contention_matrix.py` inverted-marker-polarity fix (overlap substitutions REFUSED
  into `unknown_pairs`, never recorded as disjoint pairs; dry-run reports `REFUSED (overlap
  substitution)`) + scoped-run matrix truncation fix (unmeasured rows preserved verbatim).
  145+205 tests green; validate offline OK.
- **RTG-35 OP-21 re-bench EXECUTED** (operator grant, 08:53-08:58Z, quiet host): bench-nway
  manifest-pinned ports, topology `171f86f9188211e9`, per-thread affinity attested from /proc.
  OVERLAP 8080+8185 (both node0 half `0-47,96-143`): n=3 0.977, n=6 1.194, pooled n=9 **1.121**
  (cv 0.125 — NOT decision-grade); DISJOINT control 8080+8285: **1.360** decision-grade allow
  (shipped row was 1.89 @ samples=1). Shipped 1.89 allow falsified for the production overlap shape.
  Artifacts: `data/contention_matrix/op21-overlap-rebench-20260823T0855Z/` (committed `fdd33705`).
- **Disposition APPLIED** (operator-approved): matrix pair row demoted to overlap measurement
  (ratio 1.121, cv 0.1251, samples 9, verdict `borderline`, note citing control) — `6665a923`;
  API reloaded (`reload orchestrator`, new uvicorn PID 3824001, :8000 healthy) — demotion live.
- **UFH-01 HS-OD-2** — `LLMPrimitives` fail-open `[ERROR: ...]` strings reached clients as HTTP 200;
  route now maps in-band failures to 502 (terminal SSE error event, finish_reason "error",
  REPL pre-check via `inband_error_text()`). 4 new tests failed pre-fix; 10/10 green.
- **NIB2-57a** — full `optimized_tps`/`baseline_tps` reader audit; shared `ResolvedTps`/
  `resolve_tps_prior()`/`format_tps()` in `registry_loader.py`; MCP/CLI/summary label
  baseline-stand-ins; `bilinear_scorer` fabricated `10.0` default removed (tps_known mask);
  `train_graph_router` warns on unmeasured fleet tps. 651 surface tests (1 pre-existing
  data-driven failure — `quality_overall: null` architect_general; test now data-driven).
- **SS-BENCH-GATE-b** — `scripts/server/bench_core_claim.py`: launcher reads the live bench's
  actual thread cores from /proc (fail-closed; unobservable = busy), pins default-affinity
  spawns (the incident's sidecar shape) off the claim or refuses (exit 2) unless
  `--allow-during-bench`. 60 new + 489 suite tests green.

### epyc-root
- **OBS-3** inference_guard.sh — unreadable MemAvailable now = `failed` (rc 1), never a
  WARNING-degraded all-clear (unknown means busy).
- **OBS-4** run_wrapper.sh — `autopilot_running()` three-valued via flock
  (`orchestration/.autopilot.lock`); unconfirmed suppresses shadow launch; silent skip branches →
  `AUX-DEPENDENCY-MISSING` + exit 5.
- **OBS-5** rustevo2_bench_preflight.py — three-state `autopilot_state()`; empty pgrep never
  trusted alone; `unobservable` fails preflight in strict AND advisory modes.
- **OBS-7** emergency_cleanup.sh — committed `sudo pkill -f claude` + `pgrep -f claude` DELETED;
  section refuses to guess, prints operator steps.
- Observer registry: 4 rows `unadopted` → `exempt` with reviews; `tests/test_observer_contract.py`
  26 passed post-flip.
- **NIB2-58a** (research repo + root session gate) — `verify_build_linkage.sh` helper wired into 8
  build/launch paths + `check_linkage()` in `verify_llama_cpp.sh` (frozen production launch flow);
  frozen kernel trees zero edits; live runs whisper/tts/llama CPU+HIP all PASS.
- Wiki compile sweep: 13 pages updated (hardware-optimization carries the OP-21 result;
  benchmark-methodology the SS-BENCH-GATE-b/observation-window content); lint structural clean;
  `--touch` done.

## Derived actionables filed (5)

SS-BENCH-GATE-c (API spawn layer), test_runtime_flag_spec.py drift fix, OBS-3a (mem-channel
mutation test), NIB2-58b (experimental build-dir re-point), scoring-infra loader-projection
(non-live records into live quality map). RTG-35 index row re-pointed to `_drive_admit_overlap_probes`
(bridge residual 2).

## Wrap-up mechanics

- 10 checkbox flips; index_state --check 0 problems; no prune candidates; README freshness clean.
- Commits (private-index workflow, hunk-verified, direct on main — ad-hoc session):
  epyc-root `918a709e` + `1680a0cc`; epyc-orchestrator `fdd33705` + `6665a923`;
  epyc-inference-research `65de5057`. All pushed via serialized push lock; origin/main == local.
- Operator rescue commit `f09ffe44` swept 5 of my handoff files (verified my exact edits, ancestor).
- Resolved: peer-staged deletions of OP-21 artifacts (index-only unstage — artifacts safe in
  `fdd33705`); stale peer-staged handoff/index versions in the shared index (aligned to worktree).
- Wrapup lease residue (dead `research-intake` holder) force-released + journaled.

## Open residuals (named, not deferred)

- RTG-35 → step-2 smoke bridge (`_drive_admit_overlap_probes`, shapekeyed_step2_smoke.py:718).
- SS-BENCH-GATE-c (API spawn layer) — new task filed.
- Overlap pair CV 0.125 > 0.05: measurement directional, not decision-grade (recorded honestly).
- Peer-owned uncommitted work left untouched: `src/graph/helpers.py`, `master-handoff-index.md`
  (staged), wiki/handoffs of other sessions.

## Second pass 2026-08-23 (operator: "proceed with executing these next")

All five filed residuals executed (5 parallel subagents), committed + pushed:

- **RTG-35 successor (step-2 smoke bridge)** — `_drive_admit_overlap_probes` was already implemented
  at `4dd270ed` (stale `:718` citation); added the missing fail-closed halves: `_verify_anchor_held`
  (anchor-hold precondition via read-only `active_region_holders()` scan, injectable seam) +
  `_verify_probe_signal` (refuses structurally-unobtainable plans — the stale NUMA_FULL default
  anchor previously "still reported"). Probe verified identical to `run_paired_ab._default_arm_probe`.
  12+25 tests green. **Ledger row ROUTE-A1-shapekeyed-step2 appended READY** (build gate satisfied;
  execution = dry-run + quiet window + operator anchor hold, inference-gated).
- **SS-BENCH-GATE-c** — the ONE API-runtime spawn site (`src/services/worker_pool.py:392
  _start_worker`, WARM-expansion, `numactl --interleave=all`) now guarded via `api_enforce_placement`
  (+ `ORCHESTRATOR_ALLOW_DURING_BENCH` env knob, WARNING-logged); bench-live → pins to
  `host_cores − claim` or refuses. Quiet path byte-identical. 69+179+70 tests green.
- **OBS-3a** — mutation M-D ("MemAvailable unreadable → failed", awk-shim) added; suite 15→21 passed,
  guard untouched.
- **NIB2-58b** — both launcher scripts re-pointed to `build-v9-cpu` (ground-truth: only named CPU dir
  with full binary set); verifier roots updated; live linkage runs PASS.
- **test_runtime_flag_spec drift** — `prefix_stable_order` (RTE-Prefix, default-off) added to the spec
  via the sanctioned `--sync-spec`; 22/22 green; 38 live-file drift findings left to stack owner.

Commit + push: epyc-root `…see below…`; epyc-orchestrator `7ac6870d`; epyc-inference-research `27797fef`.
