# Dynamic Stack Assembly & Concurrency Management

**Status**: COMPACTED 2026-05-28; default template realigned 2026-06-13 and DS-7 profile decision recorded 2026-07-04. Phases B-D are complete; DS-6/DS-7 design gaps are resolved and scaffolding exists. `epyc-orchestrator` `069f8c0` refreshed `stack_templates/default.yaml` to current live manifest topology with explicit aliases and retired-role rejection. `epyc-orchestrator` DS-E1 evidence packet tooling landed 2026-06-20; current packet output reports `ready_for_profile_decision=true` in `orchestration/reports/ds_e1_evidence_packet_20260705T094913Z.{json,md}`. Stack roster, DS-5 manifest freshness, contention matrix, RI-10 canary evidence, and production KV measurements are ready. Research manifest references were refreshed for the v6-era stack-prior contract, `epyc-orchestrator` `a62f9d14` validates contention evidence against measured contention roles so auxiliary launcher-only topology additions do not create false DS-E1 staleness, and `epyc-orchestrator` `c98c9e14` makes manifest freshness content-aware so same-version stack-prior recompile timestamps do not create false DS-E1 blockers when all live roles are covered. Phase E decision: retain the `default` steady-state/static-prewarm profile and park DS-6 QuarterScheduler until future evidence proves static pre-warm leaves material throughput or latency on the table. Decision artifact: `orchestration/reports/ds7_profile_decision_20260704T194020Z.{json,md}`. `epyc-orchestrator` `464aca54` now makes that profile self-policing by validating the default template's deployable ports and logical alias serving ports against generated live stack priors. Phase F KV sharing remains optional after AM/q4_0 feasibility.
**Priority**: HIGH when Phase E evidence is available; otherwise blocked/monitor.
**Domain**: routing-and-optimization primary; inference-acceleration cross-list for Phase F KVCOMM only.
**Completed ledger**: [`../completed/dynamic-stack-concurrency-completed-through-2026-05-28.md`](../completed/dynamic-stack-concurrency-completed-through-2026-05-28.md)
**Updated**: 2026-07-05

## Start Here

Do not restart DS-6 or DS-7 from first principles. The historical ledger contains the full design record and gap resolutions. The next implementer should:

1. Check whether Phase E inputs exist: Package B throughput baselines, RI-10 canary/escalation data, and DS-5/autoresearch model-stack findings.
2. If those inputs are absent, keep this handoff blocked and update the responsible source handoffs instead.
3. If those inputs are present, translate them into one stack-template/profile change, validate with `--validate-only`, then decide whether QuarterScheduler work is still justified. Current answer: `default` is the retained steady-state/static-prewarm profile.
4. Treat Phase F KVCOMM as a separate research fork; it must not block DS-6/DS-7 profile work.

2026-07-05 packet result: DS-E1 is decision-ready and machine-checkable through `scripts/server/dynamic_stack_evidence_packet.py`. Current output (`orchestration/reports/ds_e1_evidence_packet_20260705T094913Z.{json,md}`): generated stack-prior roster ready (`10` live roles, compiled `2026-07-05T08:13:39Z`), DS-5 research manifest freshness ready because `stack_priors_version=4` matches and all live roles are covered despite a compile-timestamp mismatch, contention matrix ready for full live topology `5d19b3e4edf6fc27` by validating its measured contention-role subset (`df373c79cc4af06f`) and excluding auxiliary `eval_batch_frontdoor`, RI-10 canary evidence ready, and production KV-size measurements ready. Nearby `data/kv_cache_quant/kv_quant_*.csv` artifacts are still not DS-E1 evidence: they use a different schema and contexts, lack production role rows, and must not be converted into this gate. DS-7 profile interpretation is recorded in `orchestration/reports/ds7_profile_decision_20260704T194020Z.{json,md}`: retain `stack_templates/default.yaml` as `steady_state_static_prewarm`; `python3 scripts/server/orchestrator_stack.py start --stack-profile default --validate-only` passed with `17` roles, `28` instances, and `657` GB RAM estimate.

## Outstanding Tasks

- [x] **DS-E1 — Phase E evidence packet**: collect current evidence before coding scheduler changes. `epyc-orchestrator` owns a read-only packet generator; write fresh packet artifacts with a current timestamp:
  `python3 scripts/server/dynamic_stack_evidence_packet.py --output orchestration/reports/ds_e1_evidence_packet_$(date -u +%Y%m%dT%H%M%SZ).md --strict`.
  - [~] Package B single-instance vs concurrent throughput for the roles under consideration: historical April CPU optimization data and current serving docs support the architecture direction, but the strongest numeric data predates the current June role/model map.
  - [x] RI-10 escalation/canary data for architect burst frequency: current DS-E1 packet reports canary evidence ready.
  - [x] DS-5/autoresearch model roster and role-quality findings: generated stack-prior roster is packaged, and research `docs/MODEL_MANIFEST.md` now references the current stack-prior contract. DS-E1 accepts same-version timestamp drift only when every live role is still represented.
  - [x] Production KV size measurements at 2K/8K/32K tokens: direct measurement artifacts now satisfy the DS-E1 packet gate. Keep `scripts/benchmark/ds_e1_kv_measurements.sh --execute` as the rerun harness if topology or model context changes.
  - [x] Mixed-role NUMA contention evidence, especially same-node cross-model interference: `orchestration/contention_matrix.yaml` is fresh for measured contention-role topology `df373c79cc4af06f`; full live topology is `5d19b3e4edf6fc27` because it includes launcher-only auxiliary `eval_batch_frontdoor`, which is excluded from the measured matrix check. The current serving wiki records full/quarter overlap hazards.
- [x] **DS-7-live — Profile codification from evidence**: `stack_templates/default.yaml` now carries `metadata.ds7_profile=steady_state_static_prewarm` and `metadata.ds7_decision.status=retain_default`, backed by `orchestration/reports/ds7_profile_decision_20260704T194020Z.{json,md}`. Validation command `python3 scripts/server/orchestrator_stack.py start --stack-profile default --validate-only` passed with `17` roles, `28` instances, and `657` GB RAM estimate. This records a profile decision, not a live stack change.
- [x] **DS-7-guard — Default template/generated-prior parity** ✅ 2026-07-06: `epyc-orchestrator` `464aca54` extends `validate_template()` so the production `default` profile fails if deployable role ports drift from generated live stack-prior serving ports, while alias roles pass only when their generated serving ports are covered by the alias target. Experimental templates remain flexible and embedding-only helper roles remain outside the live-prior parity surface.
- [ ] **DS-6-live — QuarterScheduler revalidation gate**: parked. Only implement dynamic quarter reassignment if future DS-E1-equivalent evidence shows static pre-warm leaves material throughput or latency on the table. If triggered, implement the already-resolved design:
  - Runtime backend mutation API: `add_instance(url)`, `remove_instance(url)`, `register_quarter(role, url)`, `unregister_quarter(url)`.
  - `QuarterScheduler` state machine with `HEALTHY/SUSPECT/DEAD/DRAINING/LAUNCHING/AVAILABLE`.
  - Quarter-fixed ports, liveness checks, drain protocol, idle-time tracking, and retry-compatible degradation.
- [ ] **DS-F1 — KVCOMM feasibility fork**: after [`attention-matching-kv-compaction.md`](attention-matching-kv-compaction.md) P2 validates coding-context compaction, prototype q4_0 offset estimation. Proceed only if shared-codebase task quality remains >95%; otherwise defer KVCOMM until f16 KV or a different sharing primitive is practical.
- [ ] **DS-F2/F3/F4 — Cache-aware routing fork**: if DS-F1 passes, design the anchor pool, wire `ConcurrencyAwareBackend` cache-aware routing, and add `prefill_speedup_coder_pool` metrics.

### Inherited from earlyoom-oom-protection closure (2026-06-12)

earlyoom is deployed and verified live ([`../completed/earlyoom-oom-protection.md`](../completed/earlyoom-oom-protection.md)); these optional residuals now live here because this handoff owns the preventive ceilings and stack-lifecycle concerns earlyoom complements:

- [ ] **Optional `--ignore` tweak**: add `claude|codex` to earlyoom's `--ignore` regex (e.g. `'^(llama-server|sd-server|claude|codex)$'` in `/etc/default/earlyoom`) to shield agent sessions — under `--sort-by-rss` a `claude`/`codex` session can otherwise be a victim before a small runaway. Non-blocking; operator edit + `systemctl restart earlyoom`.
  **VERIFIED 2026-07-29 (`auditor`) — premise CONFIRMED, prescription CORRECTED, still operator-only.**
  *Live config (pid 3761):* `earlyoom -M 41943040,20971520 -s 100,100 -r 60 --sort-by-rss --ignore
  '^(llama-server|sd-server)$' --prefer '^llama-bench$'`. So `--sort-by-rss` is on and the ignore list
  does **not** cover `claude|codex`. Premise holds.
  **The prescription as written cannot be followed from any agent session, and neither step exists:**
  `/etc/default/earlyoom` **does not exist** on this host, and this container **is not booted with
  systemd** (`systemctl` → *"System has not been booted with systemd as init system (PID 1)"*), so
  `systemctl restart earlyoom` cannot work here. earlyoom is **PPID 1, started 13:41:48 at host boot**
  — it lives outside the container entirely. This is a HOST-side operator action; the file/command
  pair in the row would send whoever picks it up on a hunt for things that are not there.
  **The rationale is stronger than the row states, measured:** thresholds are ~40 GB warn / ~20 GB kill
  (`-M 41943040,20971520` KiB) against **1133 GB total, 1115 GB available**. The largest non-ignored
  processes are `megasync` 1.1 GB and `claude` 0.7/0.6/0.6 GB, `codex` 0.4/0.4/0.3/0.3 GB. So if
  earlyoom ever fires, the memory is held by the **ignored** llama-servers, and `--sort-by-rss` would
  select a ~0.7 GB agent session against a ~20 GB deficit — **a futile kill that destroys a main
  without relieving the pressure.** That, not "agents are victims", is the argument for the tweak.
  *Not applied: host-side, operator-owned, and a restart briefly leaves the host unprotected.*
- [ ] **Open question — pause-loads-after-kill hook**: earlyoom has no built-in post-kill backoff (issue #309); mlock'd pages free slowly, so it can kill several processes in ~100 ms succession before headroom is reflected. Is a pause-new-model-loads hook (triggered by the `-N` audit hook's sentinel, or by the autopilot) worth wiring into `orchestrator_stack.py`?
- [ ] **Open question — pre-kill `-P` hook**: worth firing the autopilot host-health remediation (drop_caches/throttle-check) *before* a kill? Risk: a pre-kill script that itself allocates under memory pressure is dangerous — must be allocation-free if used.

## Dependency Graph

```text
Package B + RI-10 + DS-5 + KV-size data
    -> DS-E1 evidence packet
        -> DS-7-live profile codification
        -> DS-6-live QuarterScheduler revalidation

attention-matching P2
    -> DS-F1 q4_0 offset feasibility
        -> DS-F2 anchor pool
            -> DS-F3 cache-aware routing
                -> DS-F4 eval metrics
```

## Forks And Mitigations

| Condition | Action |
|-----------|--------|
| Phase E evidence is missing or stale | Do not code DS-6. Update the source handoffs and leave this blocked. |
| Static pre-warm is sufficient | Keep DS-6 as design-only; spend effort on DS-7 profile hygiene and monitoring. |
| QuarterScheduler is triggered | Implement drain-first reassignment; no mid-request evictions except as retry-compatible defense-in-depth. |
| KVCOMM q4_0 quality gate fails | Defer Phase F; keep AM compaction as the primary KV-size lever. |
| Disaggregated serving appears attractive | Compare against [`numa-prefill-decode-disaggregation.md`](numa-prefill-decode-disaggregation.md); prefer Sarathi-style chunked prefill before NUMA KV transfer unless measurements prove otherwise. |

## Key Files

| Repo | Path | Purpose |
|------|------|---------|
| epyc-orchestrator | `scripts/server/orchestrator_stack.py` | stack launch, profile selection, migration CLI |
| epyc-orchestrator | `src/config/stack_templates.py` | template schema, loader, resource validation |
| epyc-orchestrator | `src/backends/concurrency_aware.py` | full/quarter routing, slot save/restore primitives |
| epyc-orchestrator | `src/backends/round_robin.py` | runtime backend rotation; add/remove API if DS-6 resumes |
| epyc-orchestrator | `src/api/health_tracker.py` | circuit/health pattern for quarter liveness |
| epyc-orchestrator | `tests/unit/test_stack_templates_v2.py` | existing DS-7 validation coverage |
| epyc-orchestrator | `scripts/server/dynamic_stack_evidence_packet.py` | read-only DS-E1 evidence packet generator |
| epyc-orchestrator | `orchestration/reports/ds_e1_evidence_packet_20260704T192333Z.md` | current DS-E1 packet artifact |
| epyc-orchestrator | `tests/unit/test_dynamic_stack_evidence_packet.py` | packet generator regression coverage |

## Implementation Notes

Resolved scheduler skeleton from the ledger, reduced to the current live contract:

```python
class QuarterScheduler:
    def assign(self, role: str, priority: int) -> QuarterState:
        """Prefer idle healthy quarters, then evict the lowest-priority idle occupant."""

    def drain_for_burst(self, quarters: list[str], timeout_s: float = 30.0) -> None:
        """Mark DRAINING, stop new routing, wait for active counts to hit zero."""

    def heartbeat(self) -> None:
        """Poll /health; remove DEAD quarters from backend rotation and relaunch."""
```

The within-role placement handoff owns the full-to-quarter transition trigger and topology-safety vetoes. This handoff owns stack/profile orchestration and dynamic quarter assignment only.

## Completed Scope

| Scope | Outcome | Evidence |
|-------|---------|----------|
| DS-B observability | DS-1 queue depth, DS-2 escalation rate, DS-3 `--slot-save-path`, DS-4 stack state complete. | [completed ledger](../completed/dynamic-stack-concurrency-completed-through-2026-05-28.md) |
| DS-C pre-warm | 1x96t + 4x48t pattern documented and deployed for key roles in the historical stack. | [completed ledger](../completed/dynamic-stack-concurrency-completed-through-2026-05-28.md) |
| DS-D concurrency-aware routing | Session affinity, KV save/restore, and migration-thread design completed. | [completed ledger](../completed/dynamic-stack-concurrency-completed-through-2026-05-28.md) |
| DS-6 design audit/gaps | Dynamic URL API, liveness, quarter-fixed ports, drain protocol, idle tracking, and degradation strategy resolved. | [completed ledger](../completed/dynamic-stack-concurrency-completed-through-2026-05-28.md) |
| DS-7 template scaffolding | Template schema, selection mechanism, migration path, and resource validation designed; Gap 3/4 closure implemented 2026-04-21. | [completed ledger](../completed/dynamic-stack-concurrency-completed-through-2026-05-28.md) |
| DS-7 default-template realignment | `069f8c0` added explicit alias support/rejection of retired deployable roles and updated the checked-in default template to current live manifest topology. | `epyc-orchestrator` `069f8c0` |
| DS-E1 evidence audit + DS-7 profile decision | Current stack-prior roster, DS-5 manifest freshness, RI-10 canary evidence, production KV measurements, and contention matrix evidence are packaged; `ready_for_profile_decision=true` in the current packet. `stack_templates/default.yaml` now records `steady_state_static_prewarm` / `retain_default`, and the DS-7 decision report keeps DS-6 parked until future evidence proves static pre-warm insufficient. | `epyc-orchestrator` `orchestration/reports/ds_e1_evidence_packet_20260704T192333Z.md`; `epyc-orchestrator` `orchestration/reports/ds7_profile_decision_20260704T194020Z.md`; `python3 scripts/server/orchestrator_stack.py start --stack-profile default --validate-only` |
| DS-7 default-template prior-drift guard | `validate_template()` now checks the production default profile against generated live stack priors: deployable ports must match, and generated alias ports must be served by their template alias target. | `epyc-orchestrator` `464aca54`; `uv run pytest -q tests/unit/test_dynamic_stack.py tests/unit/test_stack_templates_v2.py`; `uv run python scripts/registry/stack_change_pipeline.py check --run-promotion-gate` |
| Research intake | DistServe/Splitwise/Mooncake/ORCA/Sarathi and SGLang hybrid-memory implications captured. | [completed ledger](../completed/dynamic-stack-concurrency-completed-through-2026-05-28.md) |

## Reporting Instructions

- Update [`routing-and-optimization-index.md`](routing-and-optimization-index.md) for DS-E1/DS-6/DS-7 status changes.
- Update [`inference-research-index.md`](inference-research-index.md) only for Phase F KVCOMM status.
- If DS-E1 blocks on missing evidence, update the source handoff for the missing evidence rather than expanding this file.
- If Phase F is abandoned or deferred, record the reason here and in [`attention-matching-kv-compaction.md`](attention-matching-kv-compaction.md).

## Research Intake Update — 2026-06-20

### drove — proactive cold-role idle-teardown (intake-701)

- DROP drove's ASR-facade idea: already shipped (`whisper_server.py` exposes OpenAI `/v1/audio/transcriptions`; `start_whisper` is a first-class managed service in `orchestrator_stack`).
- KEEP: proactive WHOLE-PROCESS idle-teardown of COLD/RARE roles (e.g. `sd_server`, `document_formalizer`) as an OPTIONAL RAM-reclaim policy (a "DS-7-profile" option), explicitly DISTINCT from the existing DS-6 quarter-eviction idle-timeout (reassigns quarters, does NOT reclaim RAM) and from earlyoom (reactive ceiling). NEVER for hot pre-warmed roles — wholesale lazy-load is an anti-pattern for our deliberately pre-warmed + mlock single-user stack. Gated on the DS-E1 evidence packet. No benchmarks (tiny project, observations).

## Research Intake Update — 2026-08-21 (Stage-2b, intake-1274 / intake-1279)

- [ ] **K4 (Z) — the frontdoor's `-ub 8192` is silently inert.** `cparams.n_ubatch = std::min(cparams.n_batch, n_ubatch)`
      and `-b` is never passed, so the effective micro-batch is the **2048 default**. Either pass
      `-b 8192` or drop the flag — as it stands the launch config misrepresents itself, and any
      reasoning that assumes an 8192 ubatch is wrong. Independent of everything else here; fix regardless.
- [ ] **G4 (G) — measure our actual post-restore prompt-reuse rate.** We call
      `/slots/{id}?action=save|restore` for full↔quarter slot migration (`llama_server.py:1242,1268`;
      `concurrency_aware.py:126,148`). Upstream issue #25913 (open, verified on master) reports restore
      **silently delivering zero prompt reuse on hybrid/recurrent models**, and open PR #26004 reports
      context checkpoints not preserved across save/restore. Our frontdoor model is `qwen35moe` —
      30 Gated DeltaNet + 10 full-attention layers — i.e. squarely a hybrid recurrent architecture.
      **SCOPE CORRECTED AND DORMANCY CLAUSE VOIDED, 2026-08-22 (Stage-2b dive on #25913/#26004).**
      **(a) The row's scope was too broad, in the direction that matters.** Reuse is zero only for a
      post-restore prompt that **diverges** from the restored prefix, or is an **exact repeat** of it.
      A prompt that **strictly extends** the restored prefix reuses **fully**. Derived from our own
      frozen source — `server-context.cpp:3320,3322` compute
      `pos_min_thold = max(0, pos_next - n_swa - (has_new_tokens ? 0 : 1))` and the reset block at
      `:3374` runs only when `pos_min >= pos_min_thold`, while `llama-memory-hybrid.cpp:172-175`
      returns the *recurrent cell's* position as `seq_pos_min` — and stated outright by the PR author.
      Four independent upstream measurements fit that table exactly.
      **Our full↔quarter migration is a turn-boundary session handover, i.e. the continuation shape.**
      So "every migration costs a full re-prefill" is NOT the default expectation; it is the failure
      mode that occurs when something rewrites the prefix. That reframes this row from *confirm a
      known loss* to *determine whether our request stream stays a strict continuation across a
      migration boundary* — a different and cheaper measurement.
      **(b) The dormancy escape is VOID — the path is LIVE.** `--slot-save-path
      /mnt/raid0/llm/cache/kv_slots/frontdoor` is set on all three frontdoor instances (8070/8080/8180,
      read from `/proc/<pid>/cmdline`); 75 `kv_migrate_*` artifacts sit on disk; live probes recorded
      forward=6 / reverse=4 with `n_aborted=0`. Qualification: those artifacts carry synthetic
      `old-sess_*` ids and the newest is 2026-08-09, so exercise by *production traffic* in the last
      two weeks is unproven — but the path is wired, enabled and demonstrably run.
      **Gate, restated:** three arms — strict continuation, exact repeat, divergence at ~50 % depth —
      at ~4K/16K/64K prefixes, reading `timings.cache_n` and `prompt_n` from the first completion
      after a restore. Continuation ≈ 0 → the feature is a net loss as configured. Continuation ≈ full
      with the other two ≈ 0 → the defect is real but our migration shape avoids it; close as
      **exposed-but-not-hit** and keep the prefix-stability guard below as the standing control.
      **THE FIXTURE MUST RESTART THE TARGET SERVER (or set `--cache-ram 0`) BETWEEN ARMS.** An upstream
      reporter lost a day to leftover in-RAM checkpoints making a broken restore look like a 340×
      success, and our frontdoor runs the 8 GiB default with no override.
- [ ] **(Z) Fix the misnamed `VERIFIED` migration state — it verifies transport, not reuse.**
      `concurrency_aware.py:679` advances to `MigrationState.VERIFIED` with `detail="restore_confirmed"`
      on an HTTP 200, and `:682` then **erases the source slot**. `n_restored` proves the file loaded,
      not that a single token will be reused. A zero-reuse migration would advance to VERIFIED, destroy
      the source, and record success. The reuse count is already available — `n_prompt_tokens_cache`
      via `GET /slots`, or `timings.cache_n` on the first completion — and `wiki/benchmark-methodology.md:257`
      already documents it as the true KV-reuse instrument. **Independent of the measurement above: the
      state is mislabelled either way.** Gate the source erase on a reuse assertion, or rename it.
- [ ] **(Z) Guard the prefix-stability assumption.** Full reuse after migration depends on the next
      request being a **byte-exact extension** of the saved prefix. Three known breakers: a rendered
      chat-template byte change, reasoning-block stripping between turns (mitigated today by
      `--reasoning off`), and any injected timestamp or preamble. Add a static check that
      post-migration request construction cannot alter bytes at or before the restored prefix boundary.
- [ ] **(G) #25592 is the LARGER exposure and should be measured first.** It fixes the **live
      in-memory** checkpoint path for hybrid/recurrent — it runs on **every request**, not only on
      migrations. It is open upstream, **absent from our tree** (`server-context.cpp:2332-2337` still
      carries the unfixed `[TAG_CHECKPOINTS_FIX_POS_MIN]` TODO verbatim), and has four independent
      verifications **including one on Qwen3.6-35B-A3B, our exact frontdoor model**.
      **Measurement:** multi-turn agentic replay at 16K/64K with `-lv 4`, counting `forcing full prompt
      re-processing` occurrences and `cache_n` per turn.
      **Gate:** a non-trivial rate of forced full re-prefill on ordinary multi-turn traffic makes
      #25592 a v10 candidate ahead of #26004.
      **Do not conflate** with the adjacent checkpoint cluster (#24055, #25472 merged, #25592 open,
      #26004): that cluster is entirely **performance** — full re-prefill, lost reuse — and produces
      no wrong output. This row is about reuse rate, not correctness.
