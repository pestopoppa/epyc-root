# Dynamic Stack Assembly & Concurrency Management

**Status**: COMPACTED 2026-05-28; default template realigned 2026-06-13. Phases B-D are complete; DS-6/DS-7 design gaps are resolved and scaffolding exists. `epyc-orchestrator` `069f8c0` refreshed `stack_templates/default.yaml` to current live manifest topology with explicit aliases and retired-role rejection. `epyc-orchestrator` DS-E1 evidence packet tooling landed 2026-06-20 and current packet output reports `ready_for_profile_decision=false`: stack roster, DS-5 manifest freshness, and contention matrix are ready, while RI-10 lacks decision-grade canary-arm evidence and direct 2K/8K/32K production KV measurements remain missing. Current RI-10 evidence is no longer a live missing-mode producer bug: since the 2026-06-20 telemetry-health start, `20` high-risk rows have `0` missing `factual_risk_mode`. The canary role scope is now widened to `frontdoor`, `worker_general`, and `worker_vision`, converting the current blocker from role-scope starvation into insufficient arm count/balance (`20` current-window arm-attributed rows, `1` enforce / `19` shadow). `epyc-inference-research` `dea5f8d` hardened the KV harness so execute mode fails closed when AutoPilot or live `llama-server` processes are present, preventing dirty-window artifacts from being mistaken for DS-E1 evidence; `epyc-orchestrator` `6f4f762c` also mirrors the port-8194 clean-window preflight in the aggregate Fable5 gate. Research manifest references were refreshed to the current stack-prior compile `2026-07-04T08:49:37Z`, and `epyc-orchestrator` `a62f9d14` now validates contention evidence against measured contention roles so auxiliary launcher-only topology additions do not create false DS-E1 staleness. Live work remains evidence-gated Phase E stack exploration, profile codification after Phase E, and optional Phase F KV sharing after AM/q4_0 feasibility.
**Priority**: HIGH when Phase E evidence is available; otherwise blocked/monitor.
**Domain**: routing-and-optimization primary; inference-acceleration cross-list for Phase F KVCOMM only.
**Completed ledger**: [`../completed/dynamic-stack-concurrency-completed-through-2026-05-28.md`](../completed/dynamic-stack-concurrency-completed-through-2026-05-28.md)
**Updated**: 2026-07-04

## Start Here

Do not restart DS-6 or DS-7 from first principles. The historical ledger contains the full design record and gap resolutions. The next implementer should:

1. Check whether Phase E inputs exist: Package B throughput baselines, RI-10 canary/escalation data, and DS-5/autoresearch model-stack findings.
2. If those inputs are absent, keep this handoff blocked and update the responsible source handoffs instead.
3. If those inputs are present, translate them into one stack-template/profile change, validate with `--validate-only`, then decide whether QuarterScheduler work is still justified.
4. Treat Phase F KVCOMM as a separate research fork; it must not block DS-6/DS-7 profile work.

2026-07-04 packet result: DS-E1 is still blocked, but the evidence state is machine-checkable through `scripts/server/dynamic_stack_evidence_packet.py`. Current output (`orchestration/reports/ds_e1_evidence_packet_20260704T090515Z.{json,md}`): generated stack-prior roster ready (`10` live roles, compiled `2026-07-04T08:49:37Z`), DS-5 research manifest freshness ready against the same compile, contention matrix ready for full live topology `5d19b3e4edf6fc27` by validating its measured contention-role subset (`df373c79cc4af06f`) and excluding auxiliary `eval_batch_frontdoor`, and RI-10 raw high-risk volume present but not decision-grade (`20` observable current-window canary-arm rows: `1` enforce / `19` shadow, below the `50` row gate). The report derives canary role scope from `classifier_config.yaml`; prior all-role diagnostics returned the same current-window count, confirming the blocker is insufficient arm count/balance rather than role-scope starvation. The current telemetry-health window is healthy (`20` high-risk rows since 2026-06-20, `0` missing mode, all inside canary scope). Production KV-size measurements at 2K/8K/32K are also absent. `epyc-inference-research` `b3a2ab6` added a clean-window DS-E1 KV harness (`scripts/benchmark/ds_e1_kv_measurements.sh`) that writes the only admissible closing artifact, `data/dynamic_stack/ds_e1_kv_measurements_<timestamp>/kv_measurements.csv`, when executed; `dea5f8d` now refuses execute mode unless the machine is clean or an explicit contaminated-run override is passed. `epyc-orchestrator` `6f4f762c` adds the same port-8194 clean-window check to `fable5_gate_report.py`, so the aggregate Fable5 gate now surfaces active AutoPilot, live llama servers, and the KV harness port as blockers. Nearby `data/kv_cache_quant/kv_quant_*.csv` artifacts are not DS-E1 evidence: they use a different schema and contexts, lack production role rows, and must not be converted into this gate. Do not implement DS-6 or DS-7 profile changes until this packet reports `ready_for_profile_decision=true`.

## Outstanding Tasks

- [ ] **DS-E1 — Phase E evidence packet**: collect current evidence before coding scheduler changes. `epyc-orchestrator` now owns a read-only packet generator; write fresh packet artifacts with a current timestamp:
  `python3 scripts/server/dynamic_stack_evidence_packet.py --output orchestration/reports/ds_e1_evidence_packet_$(date -u +%Y%m%dT%H%M%SZ).md --strict`.
  - [~] Package B single-instance vs concurrent throughput for the roles under consideration: historical April CPU optimization data and current serving docs support the architecture direction, but the strongest numeric data predates the current June role/model map.
  - [~] RI-10 escalation/canary data for architect burst frequency: raw high-risk volume is present, but corrected report semantics show decision-grade canary evidence is still missing. Latest artifacts `orchestration/reports/ri10_canary_sample_report_20260704T005256Z.json` and scope-free diagnostic `ri10_canary_sample_report_all_roles_20260704T005332Z.json` have `464` high-risk rows since canary start, `350` widened canary-role rows, and only `20` observable canary-arm rows (`1` enforce / `19` shadow), below the `50` arm-attributed row gate and `10` per-arm gate. The current telemetry-health window has `0` missing mode rows and all `20` current rows are inside canary scope; the active blocker is sample count/balance, not producer telemetry absence or role-scope filtering.
  - [x] DS-5/autoresearch model roster and role-quality findings: generated stack-prior roster is packaged, and research `docs/MODEL_MANIFEST.md` now references the current `2026-07-04T08:49:37Z` stack-prior compile.
  - [ ] Production KV size measurements at 2K/8K/32K tokens: direct measurements are still missing, but `epyc-inference-research` now has the clean-window harness:
    `scripts/benchmark/ds_e1_kv_measurements.sh --execute`. Dry-run default selects `10` production-role rows and writes executed results to `data/dynamic_stack/ds_e1_kv_measurements_<timestamp>/kv_measurements.csv`. Accepted rows must cover `frontdoor` and `ingest_long_context` at `2048/8192/32768`, plus `worker_general` and `architect_general` at `2048/8192`, with `status=ok` and `server_kv_size_mb > 0`. Execute mode now fails closed with exit `3` if AutoPilot or existing `llama-server` processes are active, unless the caller deliberately passes the `--allow-active-autopilot` / `--allow-live-llama` dirty-window overrides; the aggregate Fable5 gate also checks that the harness port `8194` is free before marking the action runnable.
  - [x] Mixed-role NUMA contention evidence, especially same-node cross-model interference: `orchestration/contention_matrix.yaml` is fresh for measured contention-role topology `df373c79cc4af06f`; full live topology is `5d19b3e4edf6fc27` because it includes launcher-only auxiliary `eval_batch_frontdoor`, which is excluded from the measured matrix check. The current serving wiki records full/quarter overlap hazards.
- [ ] **DS-7-live — Profile codification from evidence**: baseline hygiene is current after `069f8c0` aligned the default template with the live manifest topology (frontdoor/worker/ingest/vision escalation full-plus-quarter prewarm, shared-runtime aliases, one `architect_general`, 22 instances, about 653 GB). Once DS-E1 exists, create or update a stack template that expresses one concrete workload profile. Run template validation before launch. Do not add speculative profiles without evidence.
- [ ] **DS-6-live — QuarterScheduler revalidation gate**: only implement dynamic quarter reassignment if DS-E1 shows static pre-warm leaves material throughput or latency on the table. If triggered, implement the already-resolved design:
  - Runtime backend mutation API: `add_instance(url)`, `remove_instance(url)`, `register_quarter(role, url)`, `unregister_quarter(url)`.
  - `QuarterScheduler` state machine with `HEALTHY/SUSPECT/DEAD/DRAINING/LAUNCHING/AVAILABLE`.
  - Quarter-fixed ports, liveness checks, drain protocol, idle-time tracking, and retry-compatible degradation.
- [ ] **DS-F1 — KVCOMM feasibility fork**: after [`attention-matching-kv-compaction.md`](attention-matching-kv-compaction.md) P2 validates coding-context compaction, prototype q4_0 offset estimation. Proceed only if shared-codebase task quality remains >95%; otherwise defer KVCOMM until f16 KV or a different sharing primitive is practical.
- [ ] **DS-F2/F3/F4 — Cache-aware routing fork**: if DS-F1 passes, design the anchor pool, wire `ConcurrencyAwareBackend` cache-aware routing, and add `prefill_speedup_coder_pool` metrics.

### Inherited from earlyoom-oom-protection closure (2026-06-12)

earlyoom is deployed and verified live ([`../completed/earlyoom-oom-protection.md`](../completed/earlyoom-oom-protection.md)); these optional residuals now live here because this handoff owns the preventive ceilings and stack-lifecycle concerns earlyoom complements:

- [ ] **Optional `--ignore` tweak**: add `claude|codex` to earlyoom's `--ignore` regex (e.g. `'^(llama-server|sd-server|claude|codex)$'` in `/etc/default/earlyoom`) to shield agent sessions — under `--sort-by-rss` a `claude`/`codex` session can otherwise be a victim before a small runaway. Non-blocking; operator edit + `systemctl restart earlyoom`.
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
| epyc-orchestrator | `orchestration/reports/ds_e1_evidence_packet_20260704T090515Z.md` | current DS-E1 packet artifact |
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
| DS-E1 evidence audit | Current stack-prior roster, DS-5 manifest freshness, RI-10 canary evidence, and contention matrix evidence are packaged, but DS-E1 remains blocked on RI-10 widened-scope canary arm count/balance plus executed 2K/8K/32K production KV-size measurements. `b3a2ab6` added the KV harness, `dea5f8d` made execute mode fail closed outside a clean window, `6f4f762c` surfaces the harness port-8194 clean-window blocker in the aggregate Fable5 gate, and `a62f9d14` prevents launcher-only auxiliary roles from falsely staling measured contention evidence; do not implement DS-6 yet. | `epyc-orchestrator` `orchestration/reports/ds_e1_evidence_packet_20260704T090515Z.md`; `epyc-inference-research` `scripts/benchmark/ds_e1_kv_measurements.sh`; `python3 scripts/server/dynamic_stack_evidence_packet.py --json` |
| Research intake | DistServe/Splitwise/Mooncake/ORCA/Sarathi and SGLang hybrid-memory implications captured. | [completed ledger](../completed/dynamic-stack-concurrency-completed-through-2026-05-28.md) |

## Reporting Instructions

- Update [`routing-and-optimization-index.md`](routing-and-optimization-index.md) for DS-E1/DS-6/DS-7 status changes.
- Update [`inference-acceleration-index.md`](inference-acceleration-index.md) only for Phase F KVCOMM status.
- If DS-E1 blocks on missing evidence, update the source handoff for the missing evidence rather than expanding this file.
- If Phase F is abandoned or deferred, record the reason here and in [`attention-matching-kv-compaction.md`](attention-matching-kv-compaction.md).

## Research Intake Update — 2026-06-20

### drove — proactive cold-role idle-teardown (intake-701)

- DROP drove's ASR-facade idea: already shipped (`whisper_server.py` exposes OpenAI `/v1/audio/transcriptions`; `start_whisper` is a first-class managed service in `orchestrator_stack`).
- KEEP: proactive WHOLE-PROCESS idle-teardown of COLD/RARE roles (e.g. `sd_server`, `document_formalizer`) as an OPTIONAL RAM-reclaim policy (a "DS-7-profile" option), explicitly DISTINCT from the existing DS-6 quarter-eviction idle-timeout (reassigns quarters, does NOT reclaim RAM) and from earlyoom (reactive ceiling). NEVER for hot pre-warmed roles — wholesale lazy-load is an anti-pattern for our deliberately pre-warmed + mlock single-user stack. Gated on the DS-E1 evidence packet. No benchmarks (tiny project, observations).
