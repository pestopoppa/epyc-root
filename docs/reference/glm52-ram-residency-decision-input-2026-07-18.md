# GLM-5.2 RAM Residency Decision Input

Date: 2026-07-18
Scope: GC-4 operator decision input for GLM-5.2 reviewer residency.

Status update, 2026-07-19: the memory facts in this memo remain useful, but
the reviewer-quality gate changed. The executable-oracle accept-control path
converted the C-CRAB slice to decision grade, P-REV-1 ran, and GLM-5.2-IQ2
failed patch-review admission (`FA=41.7%`, `FR=25.0%`, `AUC=0.509`). GLM is
therefore diagnostic-only for patch review unless a later repair or explicit
operator route decision re-admits it.

## Decision Boundary

This memo does not decide whether GLM-5.2 becomes an always-resident A4
reviewer. It supplies the memory and process-management facts needed for the
operator decision in `handoffs/active/glm52-reviewer-capability-gates.md`.

Current recommendation input: do not treat GLM-5.2 as the production reviewer
lane. Review-window / batch launches are still physically feasible for
diagnostics, repair validation, or reviewer-model comparisons, but GLM should
not become always-resident for production patch review until a new admission
gate clears.

## Host Snapshot

`free -h` on 2026-07-18 showed `1.1Ti` total RAM, `28Gi` used, `61Gi` free,
`1.0Ti` buff/cache, and `1.1Ti` available. Swap is only `8.0Gi`, so any policy
described as "swap-in-on-demand" should be treated as cold mmap/page-cache
faulting from disk, not a real swap-backed service plan.

The host is four NUMA nodes of roughly `290GB` each. GLM's projected resident
footprint is smaller than total RAM but large enough that bad node placement can
distort latency and benchmark repeatability. Planned review windows should use
explicit interleave/affinity preflight, e.g. `numactl --interleave=all`.

## Memory Budget

All numbers are observation-grade and taken from already-recorded local
artifacts; they are enough for policy sizing, not MEASUREMENT-grade promotion.

| Component | Optimized posture | Host memory | Device memory | Evidence |
|---|---:|---:|---:|---|
| GLM-5.2 UD-IQ2_M reviewer | CPU-only, current-source GLM-DSA, 8K-16K contexts | `224372-225555 MiB` projected host; file size `222.18 GiB`; CPU_REPACK `510 MiB` | none | `/mnt/raid0/llm/tmp/glm52-dsa-long-probe-20260716T2340/logs/long_context_dsa_probe.server.log`; `/mnt/raid0/llm/tmp/glm52-current-source-16k-streaming-20260717Tpostfix/logs/long_context_dsa_probe.server.log` |
| `architect_general` | CPU optimized Qwen3.5-122B Q4, 2K/8K | `75.56-76.46 GiB` VmRSS | none | `research/deep-dives/k35-optimized-stack-throughput-context-report-2026-07-17.md` |
| `ingest_long_context` | CPU Qwen3-Next-80B Q4, default experts, 2K/8K/32K | `45.84-46.35 GiB` VmRSS | none | same K35 report |
| `worker_general` | CPU Gemma4-26B Q4 + draft, ngram+MTP, 2K/8K | `17.48-17.74 GiB` VmRSS | none | same K35 report |
| `frontdoor` optimized | MI210 resident Qwen3.6-35B Q8, no-spec/native MTP contexts | `1.37-1.40 GiB` host when GPU resident | `55-56%` MI210 alone; `~47 GiB` in MiniCPM co-residency row | same K35 report |
| `vision_escalation` approved candidate | MiniCPM-o MI210, reasoning off | `0.96-1.35 GiB` host | `~18 GiB`; combined frontdoor+MiniCPM `66-67%` VRAM | same K35 report |
| `worker_vision` current safe lane | Qwen2.5-VL CPU lane | `6.05 GiB` VmRSS | `3%` sampled | same K35 report |

Approximate all-major-service host budget with GLM resident and optimized
frontdoor/vision on MI210:

`226 GiB + 77 GiB + 47 GiB + 18 GiB + 2 GiB + 2 GiB + 6 GiB = ~378 GiB`

Using a CPU frontdoor instead of the optimized MI210 resident frontdoor adds
roughly `37-38 GiB`, putting the same rough plan near `415 GiB`. Both fit under
the host's `1.1Ti` RAM, but these totals do not include transient loaders, page
cache churn, untracked benchmark processes, or simultaneous large-model research
loads.

## Policy Options

| Option | Pros | Risks | Fit for current state |
|---|---|---|---|
| Review-window / batch diagnostic gate | Preserves normal stack repeatability; avoids pinning `~226GiB` behind a reviewer that failed P-REV-1; explicit start/stop logs are easier to audit | Cold start and page-cache warmup cost before each reviewer window | Current fit for diagnostics, repair validation, and matched ablations only |
| Always-resident interactive A4 reviewer | Physically fits; removes cold-start latency; enables interactive reviewer experiments after admission | Not justified after the 2026-07-19 P-REV-1 failure; NUMA/cache management becomes a standing service concern; can perturb CPU canonical benches | Revisit only after a new reviewer-route or repaired-GLM admission decision |
| Ad hoc cold/on-demand mmap | No standing RAM reservation | Worst process control; can fault hundreds of GiB from disk during unrelated work; `8Gi` swap cannot back this policy | Not recommended |

## Operational Preconditions For Always-Resident GLM

- A later reviewer-route decision or repaired-GLM admission gate clears the
  2026-07-19 P-REV-1 failure.
- GLM launch uses explicit NUMA/interleave policy and records per-node memory.
- The orchestrator dashboard distinguishes GLM residency from production-stack
  role capacity; GLM must not be silently treated as production registry traffic
  while it remains research-only.
- Canonical CPU benches and OP-2 quiet-window measurements do not run in the same
  window as GLM cold load or first-token warmup unless that contention is the
  measured condition.
- A stop/cleanup proof records no GLM/llama-server PID and no unintended KFD PID
  after each review-window run.
