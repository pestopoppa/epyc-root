# Dynamic Stack Assembly & Concurrency Management

**Status**: COMPACTED 2026-05-28. Phases B-D are complete; DS-6/DS-7 design gaps are resolved and scaffolding exists. Live work is evidence-gated Phase E stack exploration, profile codification after Phase E, and optional Phase F KV sharing after AM/q4_0 feasibility.
**Priority**: HIGH when Phase E evidence is available; otherwise blocked/monitor.
**Domain**: routing-and-optimization primary; inference-acceleration cross-list for Phase F KVCOMM only.
**Completed ledger**: [`../completed/dynamic-stack-concurrency-completed-through-2026-05-28.md`](../completed/dynamic-stack-concurrency-completed-through-2026-05-28.md)
**Updated**: 2026-05-28

## Start Here

Do not restart DS-6 or DS-7 from first principles. The historical ledger contains the full design record and gap resolutions. The next implementer should:

1. Check whether Phase E inputs exist: Package B throughput baselines, RI-10 canary/escalation data, and DS-5/autoresearch model-stack findings.
2. If those inputs are absent, keep this handoff blocked and update the responsible source handoffs instead.
3. If those inputs are present, translate them into one stack-template/profile change, validate with `--validate-only`, then decide whether QuarterScheduler work is still justified.
4. Treat Phase F KVCOMM as a separate research fork; it must not block DS-6/DS-7 profile work.

## Outstanding Tasks

- [ ] **DS-E1 — Phase E evidence packet**: collect current evidence before coding scheduler changes:
  - Package B single-instance vs concurrent throughput for the roles under consideration.
  - RI-10 escalation/canary data for architect burst frequency.
  - DS-5/autoresearch model roster and role-quality findings.
  - Production KV size measurements at 2K/8K/32K tokens.
  - Mixed-role NUMA contention evidence, especially same-node cross-model interference.
- [ ] **DS-7-live — Profile codification from evidence**: once DS-E1 exists, create or update a stack template that expresses one concrete workload profile. Run template validation before launch. Do not add speculative profiles without evidence.
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
| Research intake | DistServe/Splitwise/Mooncake/ORCA/Sarathi and SGLang hybrid-memory implications captured. | [completed ledger](../completed/dynamic-stack-concurrency-completed-through-2026-05-28.md) |

## Reporting Instructions

- Update [`routing-and-optimization-index.md`](routing-and-optimization-index.md) for DS-E1/DS-6/DS-7 status changes.
- Update [`inference-acceleration-index.md`](inference-acceleration-index.md) only for Phase F KVCOMM status.
- If DS-E1 blocks on missing evidence, update the source handoff for the missing evidence rather than expanding this file.
- If Phase F is abandoned or deferred, record the reason here and in [`attention-matching-kv-compaction.md`](attention-matching-kv-compaction.md).
