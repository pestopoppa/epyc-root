# HIGH upstream-impact owner reviews — 2026-11-05

Reviewer: `operator-adhoc-takeover-20261105` (operator order 2026-11-05: owner does HIGH reviews; gitnexus is a helper, not a blocker).
Method: read the pinned source with `git show <sha>:<path>` in epyc-orchestrator (no working-tree edits) and grep for every caller, including the ones gitnexus did not capture.

**What was reviewed.** No patch exists for either edit. Each row's `decision_rule` defines the planned edit by its class, and that class is what this review covers:
- KPF-26: *instrumentation for actual worker flag/checkpoint and scout request attribution*, i.e. the per-sibling, task-bound source witnesses that KPF-18.2 (2) and (3) and the KPF-26 gate call for, at `868275acb64ef3d490ecac6952518ae187fe74d3`.
- KPF-27d: *per-worker capture candidates* for the shadow-window numerators and denominators (`get_status` / `prefix_index.status`), at `326f502759986c9846027f8187972969139c0089`.

Both decisions cover **additive capture only**. An edit that changes a signature, return type, locking or admission verdict falls outside this approval and needs a new review.

## 1. KPF-26-FORKCAPS-HIGH-REVIEW — `fork_caps` — APPROVE-WITH-CONDITIONS

Evidence: `/mnt/raid0/llm/tmp/heterogeneous-slot-fabric-residency/kpf26-attestation-impact-8682-20261105-r2-q2/out/results.jsonl`. The four other symbols are LOW.

Contract (`src/scheduling/kv_pool_admission.py:644-651`): `SharedKVPoolAdmission.fork_caps(url) -> dict | None`. It **never raises**: an exception or a non-dict result becomes `None`. It is called outside the admission lock.

Callers, including the ones the graph missed:

| Caller | file:line | What it relies on |
|---|---|---|
| `SharedKVPoolAdmission.acquire` (d=1, captured) | kv_pool_admission.py:670, call at :732 | Called once per ticket **before** `with self._cond` (:735), and only when INDEX is on, a `prefix_key` is set and FORK is on. `None` means fork off. The result goes to `_prefix_index_view` (:753) as `caps`. It relies on never-raise, `dict \| None` and no lock taken. |
| `_scout_checkpoint_at` (**missed**: reached through `getattr`) | scout_stage.py:1028 | `callable(getattr(pool,"fork_caps"))`, then reads `mode`, `checkpoint_at`, `min_tokens`. Wrapped in try/except, so it returns None. |
| `_scout_trunk_prefill` (**missed**) | scout_stage.py:1061 | Same duck-typed call; the result goes to `trunk_prefill.capability`. Wrapped in try/except. |
| `_prefix_index_view` (not captured) | kv_pool_admission.py:989, call at :753 | Consumer of `caps`, not a caller of `fork_caps`. Documented as "never raises; a failure leaves the legacy decision untouched". It returns `(prefill_tokens, credit, view)`, and `acquire` reads the view keys `want`, `trunk_hold`, `lpm_score`, `fork_source_ticket`, `fork_busy_slot` and `fork_credit_tokens` **under the lock** (:767-795). |
| d≥2: `_call_caching_backend` (inference.py:1405 at 326f), passthrough `gate` → `run_upstream` (passthrough.py:550/729) | — | These reach the code only through `acquire`. They rely on `acquire` returning `int \| None`, raising `KVPoolQueueFull`, and its reservation accounting. |

Tests pin both the duck-typed contract and the flag-off contract: test_kpf21_25_trunk.py:201/285 (`fork_caps.assert_not_called()` with the flag off), test_prefix_index_flag_off.py:154-159/292, and test_prefix_index_review_fixes.py:218-225/531-575/649.

**Verdict.** Recording a witness of the caps that were read, or of the view that was derived, changes nothing any caller relies on, provided the conditions below hold. The HIGH rating comes from `acquire` being on the hot admission path for every shared-pool call, not from fragility in the contract.

**Conditions:**
1. `fork_caps` keeps its signature, keeps returning `dict | None` and never raises. The witness is recorded inside its existing try/except, or after it, and a failure to record is swallowed.
2. No witness I/O and no new lock acquisition while `self._cond` is held. Record from the values already computed outside the lock (`caps` at :732, `pview` at :753), or append to a per-ticket dict that is only read through `admission_record(ticket)`.
3. With the flag off nothing changes: `fork_caps` is not called and no new `/props` read happens. With FORK=0 no witness field may claim fork capability. Null or missing caps are recorded as `unknown`, never as a pass (the KPF-18.2 anti-vacuity rule).
4. `_scout_checkpoint_at` and `_scout_trunk_prefill` keep their duck-typed `getattr` guard. The edit must not make `fork_caps` a required attribute, because tests pass `SimpleNamespace` pools.
5. The admission verdict, `want` and the reservation accounting for each ticket are byte-for-byte unchanged.

**Regression tests that must pass:** `tests/unit/test_prefix_index_flag_off.py`, `test_prefix_index_review_fixes.py`, `test_prefix_index_admission.py`, `test_kpf21_25_trunk.py`, `test_kv_prefix_history.py`, `test_review_p2b_defects.py`, `test_kv_pool_long_prefill.py`, `test_kv_pool_unique_cells.py`, `test_kv_pool_cross_process_lease.py`, `test_inference_mixin.py`, `test_context_overflow_handling.py`.

**New tests to add:**
- (a) `acquire` with a `fork_caps` that raises and one that returns a non-dict: the ticket and verdict are unchanged and the witness says `unknown`.
- (b) A flag-off pin: `fork_caps` is never called and no witness key is emitted.
- (c) A null-witness anti-vacuity test.

## 2. KPF-27D-SHAREDPOOL-HIGH-REVIEW — `get_shared_pool_admission` — APPROVE-WITH-CONDITIONS

Evidence: `/mnt/raid0/llm/tmp/heterogeneous-slot-fabric-residency/kpf27d-impact-326f-successor-20261105-r2-q2/out/results.jsonl`. `get_status` is LOW (0 callers).

Contract (kv_pool_admission.py:1374-1378): it returns the **module singleton** `_shared_pool_admission`. Every caller relies on getting the same instance, because the queue, `_inflight` reservations, leases and stats are shared across the passthrough, primitives and scout routes in a process.

| Caller | file:line | What it relies on |
|---|---|---|
| `_call_caching_backend` (d=1) | inference.py:1405, also :1887 `report_pool_exhausted` (**missed**) | Singleton identity: the ticket acquired at :1405 is released and reported on the same object. It also uses `reservation_tokens`, `acquire` and `KVPoolQueueFull`. |
| `resolve_pool_gate` (d=1) | scout_stage.py:1102-1124 | Lazily imports and calls it only when `pool is None` and `limit.shared_pool`. Never raises. An injected `pool` overrides it, and tests rely on that. |
| passthrough `gate` (d=1) | passthrough.py:550, :557 import, :585 call | Same singleton; process `run_upstream` (:729) runs through it. |
| `src/api/admission.py:258` re-export (**missed**) | — | Re-exported name, imported by `tests/unit/test_context_overflow_handling.py:606-613`. The edit must keep the name importable from both modules. |

The four impacts the run did not capture, analysed by grep:
- `status` (prefix_index.py:1127): its only caller is `get_status` at kv_pool_admission.py:1370, under `if pi.enabled()`. It is read-only.
- `passthrough_chat_completions` / `passthrough_responses` (passthrough.py:1217-1229): FastAPI route handlers with no Python callers. They delegate to `_passthrough` and are reached only through the router.
- `run_scouts` (scout_stage.py:1210): one caller, chat.py:776. KPF-26 measured it LOW at 868275a.

**Verdict.** Per-worker capture means extra fields in `get_status()` and in the `prefix_index.status()` counters. Neither changes the accessor, so the edit is safe under the conditions below.

**Conditions:**
1. `get_shared_pool_admission()` stays a zero-argument function that returns the same process singleton. Do not use a factory, a per-call instance or per-worker instances. Per-worker identity belongs in the captured data, such as a pid or worker id field, not in the accessor.
2. The re-export from `src/api/admission.py` is kept.
3. Existing `get_status()` keys and their types are unchanged; new keys are additive only. The `prefix_index` key stays absent with the flag off. Counters are copied under `self._cond`, and no I/O happens under it.
4. An empty denominator is reported as `null` or unknown, never as 0 error. Raw numerators and denominators are emitted per window (KPF-27d box).

**Regression tests that must pass:**
- `tests/unit/test_admission.py`, `test_context_overflow_handling.py`, `test_kv_pool_cross_process_lease.py`, `test_kv_pool_long_prefill.py`, `test_prefix_index_flag_off.py`, `test_prefix_index_review_fixes.py`, `test_inference_mixin.py`, plus the passthrough and scout-stage unit suites.

**New tests to add:**
- (a) Identity: `get_shared_pool_admission() is src.api.admission.get_shared_pool_admission()`.
- (b) Flag off: the `get_status()` key set is unchanged.
- (c) An empty-denominator capture yields null, not 0.
