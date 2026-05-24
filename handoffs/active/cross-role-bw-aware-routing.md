# Cross-role BW-aware request routing + dynamic full↔quarter migration

**Status**: 🔧 DESIGN PROPOSAL — 2026-05-24 (raised from frontdoor throughput investigation)
**Owners**: routing-and-optimization-index
**Related**: [`dynamic-stack-concurrency.md`](dynamic-stack-concurrency.md) Part 2-4, [`autopilot-continuous-optimization.md`](autopilot-continuous-optimization.md)
**Source data**: `/workspace/tmp/contention_matrix_results.txt`, `/workspace/tmp/teardown_bench.log`

## Problem

The orchestrator's `ConcurrencyAwareBackend` (`src/backends/concurrency_aware.py:181-270`) handles **intra-role** request migration: when a second session arrives for frontdoor, the existing session migrates from full → quarter via `/slots/{id}?action=save`+`?action=restore` and the new session lands on a different quarter. This pattern works.

What it does **NOT** do: **cross-role contention awareness**. The router doesn't know that decoding frontdoor while ingest_long_context is also decoding craters both — they share DRAM channels on NUMA_NODE0. Autopilot's seed_batch path hits 5 different roles per trial; whenever it lands a probe on a role that's already decoding (or vice versa), the host's finite ~460 GB/s aggregate DRAM bandwidth gets split between BW-bound CPU MoE decodes, dropping each to a fraction of its solo throughput.

This is what the user saw on 2026-05-24 morning: live tap showed frontdoor at 10 t/s vs the ~21 t/s May-19 post-reboot baseline. Phase 0 benches initially attributed the gap to launcher misconfiguration; the teardown experiment (this handoff) showed the binary is fine — frontdoor delivers **24.94 t/s solo** on a clean stack — and the 10 t/s was real concurrent contention from autopilot's active probing.

## Empirical foundation (contention matrix, 2026-05-24)

Aggregate throughput = total_tokens / max(elapsed_per_role). Parallel ratio = parallel_aggregate / sequential_aggregate. Raw data: `/workspace/tmp/contention_matrix_results.txt` (v1, frontdoor-centric), `/workspace/tmp/contention_matrix_v2_results.txt` (v2 partial, other-pair coverage), `/workspace/tmp/contention_matrix_v3_results.txt` (v3, smart-pruned: skips combinations that include any already-known catastrophic pair).

### Cross-role pairs (15 measured)

| Pair | NUMA overlap | Seq agg | Par agg | Ratio | Verdict |
|---|---|---:|---:|---:|---|
| frontdoor + ingest_long_context | both NUMA_NODE0 (full overlap) | 19.52 | 7.30 | **0.37** | catastrophic |
| frontdoor + architect_general | NUMA_NODE0 ⊂ NUMA_FULL | 16.96 | 8.52 | **0.50** | catastrophic |
| ingest + architect | both heavy + node-0 overlap | 14.08 | 8.38 | **0.60** | catastrophic |
| architect + vision_escalation | NUMA_FULL + NUMA_NODE1 | 18.04 | 10.65 | **0.59** | catastrophic |
| frontdoor + worker_vision | NUMA_NODE0 ⊃ Q0B (cores 24-47) | 13.85 | 8.81 | **0.64** | loss |
| frontdoor + vision_escalation | NUMA_NODE0 + NUMA_NODE1 (disjoint) | 26.60 | 22.29 | **0.84** | mild loss |
| **worker_general + worker_vision** | 0-95 ⊃ Q0B | 16.56 | 17.74 | **1.07** | wins |
| **worker_general + architect** | both want 0-95 | 21.27 | 23.56 | **1.11** | wins |
| **ingest + worker_general** | NUMA_NODE0 + 0-95 | 25.43 | 29.98 | **1.18** | wins |
| **frontdoor + worker_general** | both 0-95, BUT gemma4 MTP | 34.64 | 44.44 | **1.28** | wins |
| **vision_escalation + worker_vision** | NUMA_NODE1 + Q0B | 14.44 | 19.15 | **1.33** | wins |
| **ingest + vision_escalation** | NUMA_NODE0 + NUMA_NODE1 | 17.60 | 25.21 | **1.43** | wins |
| **worker_general + vision_escalation** | 0-95 + NUMA_NODE1 | 37.47 | 55.44 | **1.48** | big win |

### Same-role multi-instance (frontdoor + multi-quarter aggregates)

| Combo | Seq agg | Par agg | Ratio | Verdict |
|---|---:|---:|---:|---|
| frontdoor q0 + q1 (same NUMA node) | 23.11 | 28.39 | **1.23** | wins |
| frontdoor q0 + q3 (different nodes) | 23.63 | 35.38 | **1.50** | wins |
| frontdoor q0 + q2 (different nodes) | 23.28 | 36.71 | **1.58** | wins |
| **frontdoor full + own q3** (no core overlap) | 21.52 | 36.86 | **1.71** | wins |
| **frontdoor 4-quarters concurrent (no full)** | 23.32 | 43.83 | **1.88** | big win |
| frontdoor full + 4-quarters (5-way) | 21.66 | 19.05 | **0.88** | **mild loss — adding full to 4 quarters HURTS** |
| **ingest_long_context 4-quarters** | 13.55 | 38.76 | **2.86** | **strongest signal in matrix** |
| **vision_escalation 4-quarters** ⚠️ | 26.34 | 7.75 | **0.29** | **ANOMALY — investigate** |

### Triples

| Triple | Seq agg | Par agg | Ratio | Verdict |
|---|---:|---:|---:|---|
| **frontdoor + worker_general + vision_escalation** (all pairs +) | 32.47 | 46.95 | **1.45** | wins big |
| frontdoor + worker_general + ingest (has FD+ingest catastrophic) | 21.77 | 10.61 | **0.49** | catastrophic |

### Headline findings (revised with 4× more data)

1. **Same-role quartering is the bread-and-butter aggregate winner** (1.23–2.86× sequential). The router should ALWAYS quarter when serving concurrent requests for the same role. **Ingest's 2.86× is the strongest signal** — Qwen3-Next-80B Q4 scales exceptionally well in quartered mode.

2. **The best dual-instance topology is `full + own quarter on opposite half-socket`** (frontdoor 1.71×, no core overlap, separate DRAM channels). The 5-way full+4×quarter is COUNTERPRODUCTIVE (0.88×) — the full instance contends with the quarters on cores 0-47. The dynamic-stack-concurrency design should pick EITHER full OR 4-quarters mode, not both simultaneously.

3. **Cross-role concurrency: gemma4 MTP (worker_general) is the universal good citizen.** Wins with every other role tested (1.07-1.48×) because it's so fast (~60 t/s) it usually finishes before contention matters.

4. **Cross-role concurrency: architect_general (122B Q4) is the universal bad-actor.** Catastrophic with frontdoor (0.50), ingest (0.60), vision_escalation (0.59). 122B's BW demand is so high it dominates whatever it pairs with.

5. **Quartered roles on different NUMA halves play nicely** — quarter+quarter pairs and most cross-role pairs that respect NUMA-half separation are concurrency-positive.

6. **vision_escalation 4-quarters ANOMALY (0.29×)** — solo per-quarter is 25-30 t/s, but parallel collapses to 1.94 t/s on every quarter. Suspect: --mmproj resource sharing, qwen3vlmoe-specific issue, or --override-kv expert_used_count=4 interaction. Confirmed disjoint cpusets, so it's NOT a cpu-contention issue. **Worth a dedicated investigation before relying on vision_escalation quartering in production.**

7. **The "good triple" frontdoor+worker_general+vision_escalation = 1.45×** — proves N-way concurrency is viable IF no pair is catastrophic. The lookup rule "skip if any pairwise ratio < threshold" generalizes correctly.

### What the data implies for production

- **Autopilot probing pattern** (frontdoor, worker_general, coder_escalation, ingest_long_context, architect_general per question, 5 roles × 6 questions per trial) currently triggers the catastrophic frontdoor+ingest (0.37×), frontdoor+architect (0.50×), and ingest+architect (0.60×) pairs every cycle. This is why user-facing frontdoor reads 10 t/s during autopilot runs.
- The fix is at the scheduling layer (this handoff), NOT at the per-role config. Per-role configs are correct as of 2026-05-24 (post-revert).

## Architectural target — migration-based scheduler

The 2026-04-29 [`dynamic-stack-concurrency.md`](dynamic-stack-concurrency.md) Part 2 design is exactly right; the implementation just hasn't fully landed. Recapped here with the cross-role extension the matrix data argues for.

### Routing decision tree

```
Request arrives for role X
│
├── Is any other role currently decoding with HIGH-contention pairing?
│   (per static contention matrix; e.g., X=frontdoor, Y=ingest → ratio 0.37)
│   ├── YES → QUEUE request until Y completes
│   └── NO  → proceed to slot selection
│
├── Slot selection for role X
│   ├── X's full instance idle?
│   │   ├── YES → route to full (best per-request t/s; ConcurrencyAwareBackend default)
│   │   └── NO  → X's full is busy with session S
│   │       ├── Quarter on OPPOSITE NUMA half from full's cpuset idle?
│   │       │   ├── YES → MIGRATE S from full → that quarter (KV save/restore)
│   │       │   │        Route new request to full
│   │       │   └── NO  → All quarters busy; QUEUE OR fall back to round-robin on quarters
│   │       └── (or, if migration latency unacceptable for S's context size:
│   │            route new request to a different quarter, let S finish on full)
│
└── Periodically: re-evaluate contention matrix (see "Process" below)
```

### Critical caveat — migration latency

Per the existing `/slots/{id}?action=save`/`action=restore` data: 40-50 ms for small contexts, 1-5 s for production conversations (8K-16K tokens). The matrix data shows **frontdoor full + own quarter** delivers 1.71× sequential. For that win to materialize, migration latency must be amortized over the parallel-decode period. Concretely:

- New request needs N tokens at full's degraded-rate ≈ N / 20 sec
- Migration cost ≈ 1-5 s (one-shot)
- Migration pays off when N is large enough that the per-request speedup outweighs the migration delay

For interactive/short requests, KV migration may not be worth it; better to just queue. For long-context conversations or seeding probes, it pays off.

**Decision lever**: a per-request `migration_budget_ms` (or just a token-count threshold) that lets short requests skip migration and queue instead.

### Cross-role queuing

When the router sees a request for role X arrive while role Y is decoding, it should check the contention matrix:

- `ratio(X, Y) > 1.0` → fire both in parallel (e.g., frontdoor + worker_general)
- `0.85 ≤ ratio ≤ 1.0` → fire both (mild loss tolerated for latency)
- `ratio < 0.85` → queue X behind Y (or vice versa, by priority)

Threshold (`0.85`) is a knob, exposed in autopilot's tunable params.

### Implementation primitives (already exist or near-exist)

| Primitive | Status | Location |
|---|---|---|
| `/slots/{id}?action=save`+`?action=restore` | ✅ Stable, file-based KV transfer | llama-server upstream + DS-3 wiring (`--slot-save-path`) |
| Intra-role full→quarter migration | ✅ Built but only same-role | `src/backends/concurrency_aware.py:218-270` |
| Per-role active-decode tracking | ⚠️ Partial — `_full_active` flag per role only | `concurrency_aware.py:144` |
| Cross-role contention matrix | ❌ Not in code | data lives in `/workspace/tmp/contention_matrix_results.txt` today |
| Cross-role queue/serializer | ❌ Not built | new module needed |
| Quarter NUMA-disjoint preference | ❌ Not built (router picks any idle quarter) | `concurrency_aware.py:230-260` |
| Per-pair routing override (`migration_budget_ms`) | ❌ Not built | new request-level attribute |

### Suggested phased build

Each phase ships independently and is verifiable.

**Phase A — capture the contention matrix in code**
- New file `orchestration/contention_matrix.yaml` with `(role_A, role_B) → ratio` keys, derived from the bench output
- Loader in `src/scheduling/contention.py` that exposes `contention_ratio(role_a, role_b) -> float`
- Default ratio = 1.0 for unmeasured pairs (assume parallel-neutral until measured)

**Phase B — cross-role queue with threshold**
- New `src/scheduling/queue.py` that wraps the per-role backend access with a "should we queue?" check
- Threshold `CONTENTION_RATIO_FLOOR = 0.85` (knob)
- Metrics: queue depth per role, queue wait p50/p99, contention-blocked-count

**Phase C — NUMA-disjoint quarter preference in `ConcurrencyAwareBackend`**
- Extend the quarter selection at `concurrency_aware.py:230-260` to prefer NUMA-disjoint quarters when migrating
- Encode "quarter NUMA node" in `NUMA_CONFIG`
- For frontdoor full (NUMA_NODE0) → prefer q2 (Q1A) or q3 (Q1B) over q0/q1

**Phase D — opportunistic cross-role parallelism**
- When a request arrives for role Y and role X is decoding, and `ratio(X, Y) > threshold`, fire in parallel
- Otherwise queue (Phase B)

**Phase E — migration cost / token-count threshold**
- Per-request `migration_budget_ms` (or session-context-token-count proxy)
- Skip migration for short requests; queue them instead

## Process — formalized matrix re-bench on stack changes

The user requirement: contention matrix re-bench must be **standardized as part of the stack-change flow**, not a one-off. Without this, every new model added or quant change silently invalidates the routing decisions.

### Standardized workflow

When any of these change, the matrix MUST be re-run:
- A new role is added to `stack_numa.py` `NUMA_CONFIG`
- An existing role's model / quant / NUMA binding changes
- The llama.cpp / ik_llama.cpp binary is upgraded
- BIOS / NPS / sysctl tunables change (reboot)

### Tooling to build

- `scripts/server/contention_matrix.py` — production-grade version of `/workspace/tmp/contention_matrix.sh`. Reads `NUMA_CONFIG` to enumerate role-pair benches automatically. Output: `orchestration/contention_matrix.yaml`.
- `scripts/validate/check_contention_matrix_fresh.py` — pre-commit hook that flags when `NUMA_CONFIG` mtime > matrix mtime + `--max-age 30d`.
- New `orchestrator_stack.py validate --contention-matrix` subcommand that runs the matrix + diffs against the stored YAML.

### Reporting

Per-trial autopilot logging should record which pairs were active during each request. After ≥N trials, autopilot can detect drift (measured-in-flight pair throughput vs matrix prediction) and flag matrix re-bench if drift > threshold.

## Today's frontdoor "10 t/s regression" — explained

The frontdoor throughput investigation that opened this handoff resolves as follows. The Phase 0 / matrix data shows:
- **Frontdoor solo: 24.94 t/s** ← achievable ceiling on current host
- **Frontdoor under contention (autopilot probing concurrently):** 4-10 t/s depending on which role is co-decoding

The 10 t/s screenshot reading was real concurrent contention with autopilot's seeding probes on `ingest_long_context` and/or `architect_general` (ratio 0.37 and 0.50 respectively). Not a regression, not a launcher bug, not a host-state issue. The host hasn't been re-degraded since May-20; the matrix simply shows the true cost of the orchestrator's currently-uncoordinated cross-role activity.

**Mitigation candidates for the short term, while the full scheduler is being designed:**

1. **Make autopilot's seed_batch serialize role probes more strictly.** Looking at the seeder log it already does (per-question, per-role, sequential). The contention happens because each probe takes 2-30 s and the orchestrator does NOT block parallel external requests during a probe. A simple "global decode lock" on the orchestrator would serialize external requests at the cost of dropping aggregate throughput to single-role-at-a-time.
2. **Per-role-pair lockout table** (Phase B above) — cheaper, more targeted: block requests for high-contention pairs while their counterpart is decoding.
3. **Increase autopilot inter-probe sleep** — buys quiescence between probes. Coarse but trivial.

## Decision points for follow-up plan-mode session

- **Phase ordering**: A → B → C → D → E (the natural dependency order). Skip Phase E (token-threshold-migration) until Phase D data shows migration overhead is meaningful.
- **CONTENTION_RATIO_FLOOR default**: 0.85 (from matrix data — preserves mild concurrency where it works, blocks the obvious losers)
- **Matrix storage format**: YAML keyed by sorted `(role_a, role_b)` tuple → `{ratio: float, last_measured: date, conditions: str}`
- **Migration budget**: skip migration for requests with context < 1024 tokens (predicted save time < 200ms is fine, > 200ms is worth thinking about queueing)

## Files referenced

- `src/backends/concurrency_aware.py:137-270` — intra-role migration today
- `scripts/server/stack_numa.py:44-160` — NUMA_CONFIG (source of truth for instance topology)
- `src/config/models.py:380+` — role URL bindings (`full:` prefix triggers ConcurrencyAwareBackend)
- `/workspace/tmp/contention_matrix_results.txt` — empirical data this handoff is built on
- `/workspace/tmp/teardown_bench.log` — solo-frontdoor + incremental-add log
- `handoffs/active/dynamic-stack-concurrency.md` Part 2-4 — the original design this extends

## Acceptance criteria for closure

- [ ] Phase A: contention_matrix.yaml exists, loaded by `src/scheduling/contention.py`, unit-tested
- [ ] Phase B: cross-role queue lands; metrics show contention-blocked-count > 0 in production
- [ ] Phase C: NUMA-disjoint quarter preference proven by ≥1.5× aggregate vs same-NUMA quarters under concurrent load
- [ ] Phase D: opportunistic parallelism for `ratio > 0.85` pairs lands; aggregate t/s under multi-role concurrent autopilot probing recovers toward sequential baseline
- [ ] `scripts/server/contention_matrix.py` is the canonical re-bench tool; `validate --contention-matrix` works
- [ ] Operator docs in `program.md` describe how to re-run + interpret the matrix

## Out of scope (separate handoffs)

- GPU acceleration path (different BW regime entirely)
- Model swap decisions (own concern — `autopilot-continuous-optimization.md`)
- Embedder concurrency (they don't compete meaningfully for BW; out of the matrix's scope)
