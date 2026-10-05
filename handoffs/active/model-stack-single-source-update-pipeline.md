# Model Stack Single-Source Update Pipeline

**Status**: ACTIVE — the single-source contract, runtime attestation, launch/AutoPilot/benchmark gates and swap-CI are live (history: § Completed Scope). Open work is the 2026-09-22 cutover follow-ups (SSU-F*) below; the seven boxes in § Outstanding Work are standing rules, never tasks. SSU-F17 waits on UFH-13's verdict.
**Created**: 2026-06-13
**Priority**: HIGH - stale model-specific quantities can silently corrupt
routing, scoring, launch, planner prompts, replay analysis, and operator docs
after a stack change.
**History**:
[model-stack-single-source-update-pipeline-history-2026-06-15.md](../archived/model-stack-single-source-update-pipeline-history-2026-06-15.md)
and
[model-stack-single-source-update-pipeline-history-through-2026-06-19.md](../archived/model-stack-single-source-update-pipeline-history-through-2026-06-19.md)
preserve completed chronology compacted out of this active handoff.
**Related**:
[standardized-stack-update-pipeline-finalization.md](standardized-stack-update-pipeline-finalization.md),
[model-stack-update-pipeline-audit.md](model-stack-update-pipeline-audit.md),
[model-stack-change-standardization-audit.md](model-stack-change-standardization-audit.md),
[stack-change-governance-pipeline.md](stack-change-governance-pipeline.md),
[model-capability-descriptors.md](model-capability-descriptors.md)

## Start here

- **Next:** SSU-F9c (promote-lease lock dir; `scripts/coordination/**`, so it needs a D9 ack), then SSU-F13.
- **Waiting:** SSU-F17 on UFH-13's verdict; the SSU-F1 weight deletion on the operator (its deprecation half can be
  done now); SSU-F16 on an inference window.
- SSU-F4 and SSU-F11 overlap SSU-F17.
- Also open: SSU-F8 (mostly landed in orch `b14ed228`; the owner confirms and ticks), SSU-F10, and SSU-F18 under
  § Validation.
- The seven open boxes in § Outstanding Work are standing rules. Never dispatch or tick them.

## Objective

Make orchestration-stack changes reliable by ensuring model-specific facts are
updated once, then projected everywhere:

1. edit structured truth;
2. compile generated contracts;
3. validate all consumers and docs;
4. refuse launch, AutoPilot resume, or benchmark interpretation when generated
   truth and live/runtime facts disagree.

The concrete trigger remains the stale-quantity class of bug: shared models,
retired roles, HOT/WARM status, memory footprints, context windows, launch
ports, q_scorer costs, and prompt/operator labels must not be duplicated in
unowned local constants.

## Current Baseline

- Generated model descriptors plus `orchestration/derived/stack_priors.yaml` are the source contract for live model,
  role, serving, launch, quality and memory facts. Consumers keep generated priors primary, with explicitly owned
  degraded fallbacks.
- Live checks: descriptor/stack-prior freshness, stack-manifest registry drift, q_scorer provenance, runtime
  attestation, production launch, AutoPilot preflight, direct benchmark preflight, the DS-7 template/prior parity
  guard, the launch-manifest serving-alignment validator, and (since 2026-09-23) the derived-surface checks in
  `scripts/validate/check_shared_with_derivations.py`.
- The surface manifest `orchestration/stack_change_surface_manifest.yaml` owns the hardcoded-surface inventory:
  `consumer_surface_count=13`, `rule_count=27`.
- Do not churn these re-audited surfaces unless a concrete duplicated fact reappears: `scripts.autopilot.preflight_audit`,
  `config_model_catalog` (`ServerURLsConfig` / `TimeoutsConfig` / `LLMConfig`) and the `src.config.models`
  compatibility aliases.
- X-MAS v2 (`incumbent_constrained_cheapfirst_v2`) is `promote_candidate` from the 2026-07-03 quiet-window A/B;
  production enforce stays default-off until an operator enablement decision.
- New migration work starts only from a concrete new duplicated model/role/port fact, or from a newly migrated
  consumer that deserves swap-CI coverage. The detailed baseline chronology is in the [completed sibling](../completed/model-stack-single-source-update-pipeline-completed-through-2026-09-27.md).

## Completed Scope

| Through | Historical ledger |
|---------|-------------------|
| 2026-06-15 | [model-stack-single-source-update-pipeline-history-2026-06-15.md](../archived/model-stack-single-source-update-pipeline-history-2026-06-15.md) |
| 2026-06-19 | [model-stack-single-source-update-pipeline-history-through-2026-06-19.md](../archived/model-stack-single-source-update-pipeline-history-through-2026-06-19.md) |
| 2026-09-27 | [model-stack-single-source-update-pipeline-completed-through-2026-09-27.md](../completed/model-stack-single-source-update-pipeline-completed-through-2026-09-27.md): superseded status line, detailed Current Baseline snapshot, SSU-F2/F3/F5/F9a/F9b/F9d/F9e/F12/F14/F15 and the F2/F5/F9 outcome sections |

## Required Contract

Any future stack update should be accepted only when these hold:

- generated descriptors, stack priors, procedure enums, and operator summaries
  are fresh;
- model-specific consumer surfaces are either generated from stack priors or
  explicitly owned degraded fallbacks;
- q_scorer/reward/routing/admission/launch/status/prompt consumers do not hide
  stale local model facts;
- live runtime flags, model paths, mmproj paths, context/KV/spec flags, and
  known-stack listeners agree with generated launch truth;
- scanner rules and consumer surfaces have manifest ownership metadata.

## Outstanding Work

> **⚠ THESE SEVEN BOXES ARE STANDING CONSTRAINTS, NOT TASKS — DO NOT DISPATCH OR FLIP THEM.**
> Every open box in this section is a rule with no completion state: *"Preserve … **whenever**
> migrating"*, *"Continue … **only where**"*, *"Treat … **as** re-audited surfaces … **do not churn
> unless**"*, *"Keep production routing default-off **until** an explicit operator decision"*,
> *"Keep … **under review**"*, *"Keep completed logs out of active indices"*, *"Broaden …
> **opportunistically as** consumers create new surfaces"*. Checking one asserts that an ongoing
> constraint has been permanently satisfied, after which the constraint stops being applied.
>
> **Count corrected SIX → SEVEN, 2026-08-11 (`mainC`).** The *"Treat … as re-audited surfaces"* rule
> was a standing constraint the enumeration never counted, and it had been flipped `[x]` — the exact
> false-permit C41 predicts, *"a guard that trusts an enumeration is passed by not being
> enumerated."* The banner is the scope, so an undercount silently un-guards a real rule; the repair
> belongs here rather than in a widened predicate.
>
> Noted 2026-07-29 by `auditor`. **The heading gives no warning** — "Outstanding Work" reads like a
> task list, and three of these rows (`:320`, and the two now at `:353`/`:355`) are offered as
> dispatchable in `BACKLOG-DISPATCH-QUEUE.md`'s runner-up bench. The reliable tell is the BOX TEXT
> — a continuous imperative plus a standing condition — not the section title.

- [ ] Preserve env override precedence and explicit degraded fallbacks whenever
  migrating config, runtime, benchmark, or prompt consumers.
- [ ] Continue migrating remaining high-risk P2 consumers only where a concrete
  duplicated model/role/serving fact or duplicated stack-prior traversal still
  exists; avoid broad renderer rewrites unless there is a narrow helper seam.
- [x] Re-audit `scripts.benchmark.seeding_rewards`, `scripts.benchmark.corpus_quality_gate`
  and `scripts.autopilot.kv_compress` for duplicated live facts ✅ 2026-07-29 — each imports
  generated stack-prior helpers for normal operation; each fallback remains explicitly marked
  degraded and derives from the manifest rather than copied live model/endpoint facts.
- [ ] **STANDING — do not churn `seeding_rewards`, `corpus_quality_gate` or `kv_compress`**
  unless a concrete duplicated live fact reappears. They are re-audited surfaces that keep
  generated stack priors primary with an explicit degraded fallback.
  *(SPLIT 2026-08-11 by `mainC`, adopting `auditor`'s synthesis over my own first fix. One box
  was carrying two different things: a re-audit that genuinely COMPLETED, and a rule with no
  completion state. I had restored the whole box to `- [ ]`, which hid the finished audit; it had
  previously been `- [x]`, which retired the live rule — the same loss-mode as the consumed GEAK
  pickup box. Splitting is the only form that keeps both true. Consequence for consumers: any
  queue row marking this a CLOSED task is wrong, and the dated result now lives on its own
  checked line where a completion record belongs.)*
- [ ] Broaden W4 swap-CI opportunistically as migrated consumers create new
  witness surfaces; do not add abstract fixture coverage without a migrated
  consumer to prove. Latest re-audits: the simulated vision swap already covers
  the migrated vision serving consumers (`stack_prior_vl_ports`,
  `_vl_port_for_role`, `_vl_url_for_role`, and `_vl_url_for_port`) against the
  generated stack-prior artifact, and the simulated worker swap now covers
  WorkerPool primary-port/model-path consumption plus factual-risk role-tier
  consumption after a generated worker swap. The simulated vision and
  long-context swaps also prove factual-risk role-tier consumption for their
  role classes.
- [x] Fix promotion-gate test regressions: `_role_result` fixture missing
  `tool_chains` attribute (orchestrator `91cb03bf`), and stale ingest
  topology fixture expectation (`083e2736`). Full promotion-gate `181 passed`,
  pipeline `summary: ok`. ✅ 2026-07-07
- [x] Deploy/reload the repaired X-MAS constrained policy and rerun the
  held-out quiet-window A/B with required policy
  `incumbent_constrained_cheapfirst_v2`; the 2026-07-03 artifact is
  `promote_candidate` with no blockers.
- [ ] Keep production routing default-off until an explicit operator
  enablement/reload/attestation decision accepts the repaired-policy evidence.
- [ ] Keep `scripts/autopilot/short_term_memory.md` under review as live run
  state; do not prune it during active AutoPilot execution.
- [ ] Keep completed implementation logs out of active indices; record future
  closures in `progress/` and compact/archive at wrap-up.

## Validation

Default no-inference acceptance:

```bash
uv run python scripts/registry/stack_change_pipeline.py check
```

Promotion/launch-boundary acceptance:

```bash
uv run python scripts/registry/stack_change_pipeline.py check --run-promotion-gate
```

Surface inventory checks:

```bash
uv run python scripts/validate/stack_change_guard.py --surface-summary-only --all-hardcoded-surfaces
uv run python scripts/validate/stack_change_guard.py --list-hardcoded-surface-rules --surface-inventory-format json > /tmp/stack-change-inventory.json
```

Moved-lineup regression (from SSU-F5): the pytest plugin `/mnt/raid0/llm/tmp/ssuf5/moved_lineup.py`
relocates the worker lane a second time, onto `architect_critic`. Against `tests/unit/test_stack_priors_compiler.py`
it gives 34 of 35 passing; the one failure is the deliberate pin. It lives only in tmp, beside its fixtures
(`launch_manifest.yaml`, `model_registry.yaml`, `moved/`).

- [ ] **SSU-F18 — commit the moved-lineup plugin to the orchestrator tests** before a disk reclaim removes
  `/mnt/raid0/llm/tmp/ssuf5/`. Bring its fixtures with it, run it against `tests/unit/test_stack_priors_compiler.py`,
  and keep the 34/35 result, with the deliberate pin failing, as a standing regression against the next lineup change.
  Zero inference. **Blocker: none.**

---

## Follow-ups from the 2026-09-22 v10 promotion + lineup cutover

The cutover is live and serving; these are what it left owed. Each names its own
blocker rather than sitting in prose.

Closed and moved to the [completed sibling](../completed/model-stack-single-source-update-pipeline-completed-through-2026-09-27.md): SSU-F2, F3, F5, F9a, F9b, F9d, F9e, F12, F14, F15, and the F2/F5/F9 outcome sections. SSU-F9 is ticked below.

- [ ] **SSU-F1 — deprecate the seven `*_local` catalogue rows for the retired models, THEN delete ~544 GiB of weights.**
  The lineup change deprecated the role-holding rows and never touched the
  exact-artifact rows beneath them, so `qwen35_122b_iq2m`,
  `qwen3_next_80b_a3b_instruct_iq2m_local`, `gemma4_26b_a4b_orig_q8_local`,
  `gemma4_26b_a4b_q4km_current_local`, `gemma4_26b_a4b_orig_bf16_local`,
  `gemma4_26b_a4b_ud_iq4xs_local` and `draft_gemma4_26b_a4b_assistant_v6_f16_local`
  are all still live and non-deprecated. Three of them ALREADY point at absent
  files. Deleting before deprecating leaves seven rows naming missing artifacts.
  Clean checks already pass: no process maps them (`/proc/*/maps`), no live
  serving role references them. Use the `retire-model` skill — this is exactly
  what it refuses on. **Blocker: deletion is an operator action (destructive,
  irreversible); the deprecation half can be done now.**

- [ ] **SSU-F4 — make the stack-change surfaces derive instead of restate.**
  The audit's structural finding (`artifacts/operator/session-friction-audit-20260922.md` §2):
  `port_map`, `role_launch_meta`, `numa_config`, the procedure enums and
  `roles.*` each independently restate `shared_with`, and nothing recomputes.
  The `stack-change` skill now enforces the discipline by hand; the durable fix
  is to derive them. **Blocker: none — design work, sizeable.**

- [ ] **SSU-F8 — `src/config/models.py::_LEGACY_SERVER_URL_FALLBACKS` still names the retired `:8072`
  worker fleet, and eleven neighbouring tests assert the same dead ports.** Found by SSU-F5 while
  reading, reported rather than fixed because it is outside one test file.
  Three rows — `worker_general`, `worker_math`, `toolrunner` — carry
  `full:http://localhost:8072,http://localhost:8082,http://localhost:8182`. Those ports have not
  existed since 2026-09-22; all three roles are aliases on frontdoor `:8070`. `_server_url_default()`
  ends in a bare subscript of this dict, so in **exactly the degraded mode the table exists to serve**
  (priors unreadable, no runtime facts, fresh checkout, bootstrap) these three roles resolve to a fleet
  with nothing listening. It reads correct today only because live runtime facts win.
  `worker_summarize` and `coder_escalation` were updated at their cutovers; the worker lane was not.
  **Do not just update the three rows.** Add `_LEGACY_SERVER_URL_FALLBACKS` as a **sixth surface** in
  `scripts/validate/check_shared_with_derivations.py` — an alias's fallback must equal its host's,
  recomputed and diffed. It is the shape that file already handles, and its absence is the whole reason
  this rotted silently while the five wired surfaces did not.
  Then clear the eleven pre-existing failures in the neighbouring suites (verified present without
  SSU-F5's change; none of them import the file it edited):
  `test_config.py` ×2 (the consumer-side twin of the defect above), `test_config_lineup_liveness.py` ×1
  (`KeyError: 'worker_general'`), `test_stack_numa_reader_agreement.py` ×2, `test_stack_numa.py` ×1,
  `test_stack_manifest_imports.py` ×4, `test_stack_change_guard.py` ×1.
  **Two of those deserve attention beyond "stale literal".** `test_stack_numa_reader_agreement`
  (`assert [8080] == [8080, 8180]`) is a reader *disagreeing about half-instance ports* — the only
  failure whose cause is not obviously a copied constant, and worth looking at independently of tests.
  And two of the four `test_stack_manifest_imports` failures are a **stale parity exception still live
  in `launch_manifest.yaml`**, whose own text says it no longer applies; while it sits there it
  pre-excuses the next real divergence. One line, a live surface, owned by whoever owns that file.
  **Blocker: none.**
  *Progress 2026-09-23 (orch `b14ed228`, an ancestor of origin/main):* `_LEGACY_SERVER_URL_FALLBACKS` is now the sixth derived surface in `check_shared_with_derivations.py`, wired into `stack_change_pipeline` before the lean compile. On its first run it found four stale rows, not three (`ingest_long_context` also named a retired fleet). The six neighbouring suites went from 11 failed / 288 passed to 299 passed. The commit judged the reader-agreement failure not a production defect, and found that the "stale parity exception" did not exist (`exceptions: []` since 2026-08-02; the parity tests had gone vacuous). Left open for the owner to confirm against this box's full scope and tick.

- [x] **SSU-F9 — a correctly-acquired push lock does not satisfy the pre-push guard, and the failure
  mode is silent.** Measured 2026-09-23: four consecutive failed pushes of one reviewed commit.
  Two independent defects compose, and each one alone is enough to block a push while reporting success:
  **(a) the lock directories disagree.** `serialized_push.py` with no `--lock-dir` derives ONE canonical
  directory from the git common dir (correct, and deliberate — it is what makes all five lane worktrees
  contend for one lease). The pre-push hook looks in `<repo>/coordination/push-locks/`. So `--acquire`
  reports `acquired push lock for .` and the hook then reports `the push serialization lock is NOT HELD
  — no lock file at /workspace/coordination/push-locks/push-<key>.json`. Both are telling the truth
  about different directories.
  **(b) the wrapper's own `--push` cannot satisfy its own guard across two tool calls.** The guard
  accepts a push whose process is a *descendant of the lock holder*, but `--acquire` and `--push` run as
  separate processes, so the holder pid is not an ancestor and the check falls through to
  `EPYC_PUSH_LOCK_HOLDER`/`AGENT_ID` — neither of which the wrapper exports. The push fails.
  **The silence is the real defect**: `--push` prints its full publish manifest and then
  `PUSHING as '<agent>' under the push lock ...` as its LAST line, while git's `error: failed to push
  some refs` goes to stderr and surfaces *before* the manifest. A caller reading the tail sees a
  clean-looking manifest ending in `PUSHING`, and `--release` afterwards says `(no push lock held)`,
  which reads like a normal post-push release. Nothing in that sequence says the push did not happen.
  Only `git cherry origin/main main` does — which is why the wrap-up contract requires it.
  Fix: make the guard and the wrapper agree on one lock directory; have `--push` exit non-zero and say
  `PUSH FAILED` on the last line; and have the wrapper export its own identity so its push satisfies its
  own guard. **Blocker: none.**
  ✅ 2026-09-23 — fixed in root `0f9a4ef1` (verified an ancestor of origin/main 2026-09-27): guard and wrapper share one lock resolver, the wrapper declares `EPYC_PUSH_LOCK_HOLDER` for its own push, and `--push` verifies with `git cherry` and ends on `PUSH VERIFIED` / `PUSH FAILED` (exit 4). The D9 ack is in the commit (SSU-F9a). Outcome, SSU-F9a and SSU-F9b: [completed sibling](../completed/model-stack-single-source-update-pipeline-completed-through-2026-09-27.md).

- [x] **SSU-F9c — `promote_lane.py:519` has the same defect one lease over.** It defaults
  `--lock-dir` to `serialized_push.DEFAULT_LOCK_DIR`, the `__file__`-relative fallback, which in a
  lane worktree is that lane's **private** directory — so the *promote* lease serializes nothing
  across lanes, exactly the 2026-09-01 incident that the push lease's git-common-dir derivation was
  introduced to fix. ✅ 2026-10-05: default promotion lease now uses the target's git common
  directory via `serialized_push.default_lock_dir`; environment/CLI overrides remain explicit.
  Accepted CI run [37273697465](https://github.com/pestopoppa/epyc-root/actions/runs/37273697465),
  combined source `23298f00096f24b5d665a478467692f2085c09a0`: three focused fixtures passed,
  including two real worktree leases contending for one lock. No actual promotion was executed.

- [ ] **SSU-F10 — every GPU role on this host is un-auditable for VRAM between reloads, by
  default.** The per-buffer breakdown (`load_tensors:`, `llama_kv_cache:`,
  `llama_memory_recurrent:`, `sched_reserve:`) is suppressed at the launcher's default log
  verbosity, which is why SSU-F3 had to be answered by subtraction in the first place — and why the
  subtraction was wrong by 0.277 GiB. The 2026-09-23 reload settled `:8083` only, and only until it
  next restarts. Raise the model-load log verbosity permanently in the launcher so the decomposition
  is in the log of every GPU role from the moment it starts. A capacity model that cannot be checked
  against the kernel's own numbers is a model nobody can falsify. **Blocker: none.**

- [ ] **SSU-F11 — the registry's `recipe:` block is DECORATIVE: nothing reads it, and the served
  process runs a hardcoded parallel configuration.** Root-caused 2026-09-23 while chasing SSU-F7's
  two missing env knobs on `:8074`. The knobs are only the visible edge.

  **The measurement.** `architect_critic` declares, in `model_registry.yaml` under
  `recipe: {recipe_id: qwen38-flash-next-cpu-mtp}`: `threads: 48`, `cpu_shape: NUMA_FULL_T48`, and
  `env: {GGML_NOHUGEPAGE_PROCESS: '1', GGML_FA_SPLIT_KV: '0'}`. The live process (pid 2021760) runs
  `-t 96`, and its `/proc/<pid>/environ` contains `GGML_IQK=1` and the four OMP vars and **none of
  the declared knobs**. `no_mmap`, `-ctk/-ctv f16` and `--spec-draft-n-max 4` do match — but they
  match because the *launcher* and the `acceleration:` block independently say so, not because
  anything consulted `recipe:`.

  **Why: there is no reader.** `grep` for any consumer of `recipe.env` across `scripts/` and `src/`
  returns **zero hits**. `build_launch_env()` (`scripts/server/stack_env.py:258`) composes its env
  from a base copy, a canonical OMP block, and `_role_env_overrides()` — which reads
  `_ROLE_ENV_BLOCKS`, a **hardcoded dict in that file**. For `architect_critic` that dict holds
  exactly `{'GGML_NUMA_REPACK_INTERLEAVE': '0'}`, and not one of the eight role blocks mentions any
  of the three recipe knobs. `GGML_IQK=1` is live because it is a launcher default, not because the
  recipe asked for it — which is precisely why this looked like it was working.
  `cpu_shape: NUMA_FULL_T48` has no definition in `stack_numa.py`, which is why the thread count
  falls through to 96.

  **Why it matters beyond hygiene.** `GGML_NOHUGEPAGE_PROCESS=1` is **CHAMP-2, ADOPTED 2026-09-08 by
  operator ruling** (`model_registry_full.yaml:1758` says so in its own comment), it is a
  SESSION-unit knob that must be exported AT LAUNCH, and it is not being exported. An adopted,
  operator-ruled optimisation is not reaching production and nothing detects that.
  **State direction only, never a magnitude**: `qwen38_flash_next_recipe.py` sets
  `THP_SHIM["magnitude_claimed"] = False` deliberately, and the 86.4% figure in that module's tests
  is about conflating the two THP knobs discarding most of the CHAMPION, not about this shim's own
  effect. Do not quote it as the shim's value.

  **Fix shape** — the same one SSU-F8 used, and for the same reason: derive, then make disagreement
  detectable. Have `build_launch_env()` read `recipe.env` from the registry, with `_ROLE_ENV_BLOCKS`
  either removed or reduced to a documented override layer; resolve `cpu_shape` against
  `stack_numa.py` and FAIL on an undefined shape rather than silently falling through to a default;
  and add "the served process's env and thread count equal its declared recipe" as a surface in
  `scripts/validate/check_shared_with_derivations.py`, which is now the established home for exactly
  this check. A declared recipe that nothing reads is not a source of truth, it is a comment.

  **Carry this into any claim measured on `:8074`.** The architect CPU quality gate runs against
  this process, so its rows are `instrument_class: serving` AND the served configuration is not the
  recipe's — `-t 96` where the recipe measured `-t 48`, without the THP shim. The recipe's recorded
  43.281 t/s decode was measured at `t=48` WITH the shim on the champion build, so it cannot be
  expected to describe this process, and the two must never be quoted against each other.
  **2026-09-27 — the `threads: 48` / `NUMA_FULL_T48` claim is SUPERSEDED by measurement.** DAR-LAT-3h's signed G1
  (v10, served shape) chose **T96**: 48 threads failed parity (wall 1.0385×, TTFT 1.055× vs 96) and the THP shim gave
  no gain (1.009×). So the 2026-09-22 C3 ruling's premise ("48 is the served decode optimum") no longer holds, live
  `-t 96` is the right shape, and nothing was applied. The recipe text still says 48 because the correcting research
  lane was not merged either; when this task makes `recipe:` load-bearing, it must derive 96, not 48. Evidence:
  `artifacts/operator/stack-change-dar-lat-3h-20260926/RESULT.md`.
  **Blocker: none.**

- [ ] **SSU-F13 — 10 more unit tests still encode the pre-cutover topology.** Fail on clean origin/main
  (2026-09-24, after `8d7633d0`): `tests/unit/test_default_template_topology_parity.py` (9 — e.g.
  `ingest_long_context` now alias-only, `worker_general` has no `NUMA_CONFIG` instance) and
  `tests/unit/test_stack_templates_v2.py::test_default_yaml_loads_and_validates`. Per test: decide stale
  fixture (derive from the source of truth, as SSU-F5) vs. a real template defect; do not re-pin constants.
  - *2026-09-24 confirmation:* the `worker_general` / `NUMA_CONFIG` `KeyError` reproduces read-only in the
    SHARED clone (`/mnt/raid0/llm/epyc-orchestrator`, `main`, unrelated dirty files in `src/services/image_*`)
    via `.venv/bin/python -m pytest -q -p no:cacheprovider tests/unit/test_fleet_layer_dispatch.py` — same
    `KeyError: 'worker_general'` at collection. This is **real pre-cutover drift, not a worktree-only config
    gap.**
  - [ ] A wider `tests/unit` sweep reported by an agent this session found **~96 failures / 38 errors**,
    which is far more than the 10 named above — re-run the full `tests/unit` suite, bucket every new failure
    by root cause (same topology-parity class vs. genuinely new), and fold the ones that match this item's
    scope in; file any that don't as their own row.
- [ ] **SSU-F16 — build the architect_critic CRITIC-SUITE instrument and run it on Qwen3.8-Flash-Next.**
  Operator chose option A on 2026-09-24 (orch `9692c7f9`, merged in `d7ab368e` on
  `fix/promotion-gate-red-20260924`). Strict now counts `performance.general_suite_quality`
  (mmlu_pro 0.7550 / gpqa 0.6513) as per-axis evidence, never as `overall`, so the gate no longer blocks
  on it. The role-purpose gap that research `58b115ed` deliberately left open is **still open**:
  `quality_score` means the adversarial-critique suite on this role, it stays null, and no critic-suite
  instrument exists anywhere. Build one (plan-critique items, DELETE-lens scoring, truncation audit per
  `promotion_gates.yaml`), run it on live :8074 at a CPU-quiet boundary, and record the result in
  `roles.architect_critic.performance.quality_score`. Blocker: none (buildable); the run needs an
  inference window. Emit producer-authored belief rows from the first run, as the SSU-F2 CPU bench does
  (root `CLAUDE.md` → *Belief Kernel*).

- [ ] **SSU-F17 — key servers by model instance and bind every role to a server id.** **Sequenced after UFH-13
  (operator 2026-09-27)**: approved in chat (session https://claude.ai/code/session_01FKXdQsgLuwnFVWQ3npGfrJ) to run
  AFTER the thesis experiment (`thesis-experiment-orchestrator-vs-strongest-model.md`), not before or during it.
  - **The limit today.** `server_mode.<key>` is both a role name and a process declaration, so a server has no name
    except its owning role's. An alias binds role → role through `server_mode.<host role>.shared_with`, and
    `alias_of` is documentation only. When a role label moves between processes, every alias must be re-pointed by
    hand across about 8 restated surfaces. ARCHSWAP-20260927 had to do exactly that.
  - **The change.**
    - Add a server namespace keyed by model instance (e.g. `servers.qwen38_27b_q8_gpu0 {port, model, shape, ...}`).
    - Every role, host or alias, binds to a server id.
    - Retire the role → role binding through `server_mode.<host role>.shared_with` and the documentation-only
      `alias_of`, with their validators and derived restatements (`shared_with_first_n`, the alias `server_mode`
      rows that must equal the host's port).
    - Roles stay distinct prompt and tier profiles: `orchestration/prompts/roles/{role}.md` and per-role
      `chat_template_kwargs` stay per role.
  - **Done when** a role swap like ARCHSWAP is a two-line change to two roles' server ids and no alias moves.
  - **Evidence.** ARCHSWAP PACKAGE §4a,
    `/mnt/raid0/llm/tmp/archswap-20260927/root/artifacts/operator/stack-change-archswap-20260927/PACKAGE.md` (root
    `lane/archswap-20260927`). Code refs (orch `280059cc`): `src/registry/stack_priors.py:900-907`
    (`_server_for_role`), `src/registry/registry_compiler.py:117-119`, `src/registry/model_descriptors.py:1285-1300`,
    `scripts/validate/check_shared_with_derivations.py:400-442` (`check_alias_of_coherence`).
  - Overlaps SSU-F4 (derive instead of restate): once roles bind to server ids, the `shared_with` alias lists that
    SSU-F4 would derive no longer exist.
  - Also fold in ARCHSWAP acknowledgement **A-5**, a pre-existing defect the swap did not cause:
    `ingest_long_context` is in `serial_roles`, but its host server is not. Once roles bind to server ids,
    serial-ness belongs to the server. Derive it there, so an alias can no longer disagree with its host. (Folded here
    2026-09-27 rather than filed separately: a stand-alone fix would re-edit a surface this task deletes.)
  - It changes the registry schema, so it runs as a `stack-change` package with one operator signature.
  - Not folded here (2026-09-28): `coder_escalation`'s dead `enable_thinking: False` (it inherits its host's
    thinking-on lane) is reconciled under `routing-intelligence.md` RI-23a, because it is needed before TE-reopen.
    RI-23a was applied 2026-09-29 (receipt `RATIFY-RI23A-20260929`): the role is thinking-on in the registry and the
    priors.
  - Blocker: sequencing only (UFH-13's verdict, TE-6).

2026-10-05 NI18 fullscan checkpoint accepted: all895 tracked unit modules have independently reopened original native receipts and deterministic selection/source/hash accounting across32 shards. Outcomes826TRUE57FALSE12NULL;16,227 collected/15,719 passed/258 failures/68 errors/182 skipped. This is capture/accounting acceptance, never whole-suite conformance. Originals remain unchanged in CI37327810408 and owned custody; [derivative inventory](../../artifacts/ni05/unit-sweep-37327810408/README.md) records the distinction. A prospective nine-module fixture rerun prepares only missing owned0700 runner scratch; parentNI18/SSU-F13 remains open for classification/repairs. Running tally **35/38**.

- [ ] **SSU-FIXTURE-KVSLOTS (NI05-39)** — original fullscan modules `test_build_server_command_helpers.py` (8 failures of74) and `test_k4_ubatch_not_inert.py` (3 failures of11) fail at mkdir of `/mnt/raid0/llm/cache/kv_slots/{role}` on ephemeral CI. Main source review confirms argv-building fixtures with existing process/health stubs. Prepare/attest only the runner-owned0700 cache fixture and run the two unchanged modules independently through existing native CI custody. No serving, kernel-store simulation, host/peer/live KV writes or source policy change. Scope and exact prospective recipe receive main review; preserve original FALSE receipts.

NI18 scratch-fixture phase independently accepted from original CI37331885023: all nine unchanged test modules reopen TRUE Judged/Located;312 collected282passed30skipped0fail/error, separate ordinary guard1/1. Runner-only owned0700 scratch preparation resolves the observed path failures while preserving fence assertions. Earlier895-module FALSE/NULL originals are unchanged; this is no whole-suite pass. NI39 cache-fixture follow-on is newly filed; tally **35/39**, NI18/37/38/39 continue.
