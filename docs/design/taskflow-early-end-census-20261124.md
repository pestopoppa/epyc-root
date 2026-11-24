# Taskflow early-end census (2026-11-24)

**Decision rule:** BUILD a resumable end state if early-ends are at least 25% of all failures across r8a–r8g **and** at least two early-ended units plausibly would have finished after one resume, having stopped mid-task with recoverable state. Otherwise DECLINE.

**Verdict: DECLINE.** There are **0 early-ends among 50 failures (0/50 = 0%)**, and therefore zero demonstrated candidates for one-resume recovery. Both conditions fail. This is a census of these runs, not a claim that early-ends cannot occur elsewhere.

## Counts

Each row counts units once. Failures are all categories except completed; the share is early-ends divided by failures, with no-failure rows shown as —.

| Round | Arm | Completed | Early-end | Timeout | Harness refusal | Model error | Early-ends / failures |
|---|---|---:|---:|---:|---:|---:|---:|
| r8a | easy-nothink | 5 | 0 | 0 | 0 | 0 | — |
| r8b | canary-nothink | 1 | 0 | 3 | 3 | 1 | 0/7 (0%) |
| r8b | canary-think | 0 | 0 | 5 | 3 | 0 | 0/8 (0%) |
| r8c | canary-nothink | 3 | 0 | 0 | 2 | 2 | 0/4 (0%) |
| r8c | canary-think | 0 | 0 | 2 | 4 | 1 | 0/7 (0%) |
| r8d | canary-nothink | 0 | 0 | 0 | 5 | 0 | 0/5 (0%) |
| r8d | canary-think | 0 | 0 | 0 | 5 | 0 | 0/5 (0%) |
| r8e | canary-nothink | 3 | 0 | 0 | 2 | 0 | 0/2 (0%) |
| r8e | canary-think | 3 | 0 | 1 | 0 | 1 | 0/2 (0%) |
| r8f | canary-nothink | 2 | 0 | 1 | 1 | 1 | 0/3 (0%) |
| r8f | canary-think | 2 | 0 | 2 | 0 | 1 | 0/3 (0%) |
| r8g | canary-nothink | 3 | 0 | 0 | 1 | 1 | 0/2 (0%) |
| r8g | canary-think | 3 | 0 | 0 | 1 | 1 | 0/2 (0%) |
| **Total** | **all** | **25** | **0** | **14** | **27** | **9** | **0/50 (0%)** |

## Unit classification and evidence

Within each arm the names below enumerate every recorded unit. C = completed, E = early-end, T = timeout, H = harness refusal/failure, M = model error or other remaining non-timeout failure. A timeout takes precedence over any subsequent verifier rejection or transport error. A 30-step cap is budget exhaustion, not a voluntary early end, even when wall time remains. A finished but incorrect or rejected deliverable is not an interrupted mid-task worker. Harness refusal includes failed brief/lane admission, incorrect verifier rejection, and the lost lane in r8f; M also includes the r8c stale NUMA packet, which is a packet problem rather than a model fault. These two broad labels accommodate the requested five-category partition; they do not override the root-cause audit.

- **r8a easy-nothink:** C E1-SQUARE, E2-RENAME, E3-OFF-BY-ONE, E4-TIMEOUT, E5-TYPO. E4 is a task name, not a timeout.
- **r8b canary-nothink:** C NOFOLD-1; T INTAKE-VALIDATE-86, WS4-WAKE-IMPERATIVE, MM-5; H TU-GR-1, NUMA-DECOUPLE-1, UFH-21; M LOOP-62.
- **r8b canary-think:** T INTAKE-VALIDATE-86, TU-GR-1, LOOP-62, WS4-WAKE-IMPERATIVE, MM-5; H NUMA-DECOUPLE-1, NOFOLD-1, UFH-21.
- **r8c canary-nothink:** C TU-GR-1, LOOP-62, NOFOLD-1; H INTAKE-VALIDATE-86, NUMA-DECOUPLE-1; M WS4-WAKE-IMPERATIVE, MM-5.
- **r8c canary-think:** T INTAKE-VALIDATE-86, LOOP-62; H TU-GR-1, NOFOLD-1, WS4-WAKE-IMPERATIVE, MM-5; M NUMA-DECOUPLE-1.
- **r8d both arms:** H TU-GR-1, LOOP-62, NOFOLD-1, WS4-WAKE-IMPERATIVE, MM-5. Lane-cap refusals prevented all model requests; the round was superseded. It is included in the rule's denominator as specified; excluding its 10 failures still gives 0/40.
- **r8e canary-nothink:** C NOFOLD-1, WS4-WAKE-IMPERATIVE, MM-5; H TU-GR-1, LOOP-62.
- **r8e canary-think:** C LOOP-62, NOFOLD-1, MM-5; T WS4-WAKE-IMPERATIVE; M TU-GR-1.
- **r8f canary-nothink:** C LOOP-62, NOFOLD-1; T WS4-WAKE-IMPERATIVE; H MM-5; M TU-GR-1.
- **r8f canary-think:** C NOFOLD-1, MM-5; T LOOP-62, WS4-WAKE-IMPERATIVE; M TU-GR-1.
- **r8g canary-nothink:** C LOOP-62, NOFOLD-1, MM-5; H WS4-WAKE-IMPERATIVE; M TU-GR-1.
- **r8g canary-think:** C LOOP-62, NOFOLD-1, MM-5; H TU-GR-1; M WS4-WAKE-IMPERATIVE.

The r8e think and r8f nothink TU-GR-1 records say verified, but the hand audit found vacuous isolation tests; both are counted as M. Conversely, r8c think NOFOLD-1 and WS4 had acceptance-passing work rejected by the reviewer, and r8g think TU-GR-1 was a reviewer false reject; these are H, not early-ends. The r8f nothink MM-5 worker removed its own lane after its tests passed, so its lost diff is a harness failure, not recoverable session state. r8c think NUMA reported the task already done against a stale packet; it did not stop mid-task. The audit notes a live-session acceptance gap in r8e nothink WS4; this census counts its audited acceptance-scope completion, not closure of the wider box.

Sources: per-unit `worker/events.jsonl`, `ledger.jsonl`, diffs and `out/results.jsonl` under `/mnt/raid0/llm/tmp/taskflow-stage1-cpu-r8*-*/out/`; `out/verdict.json` where present; [canary hand audit](taskflow-stage1-canary-findings.md); `scripts/coordination/taskflow/harness/local_llm.py` and `verify.py`. The r8b data is in `taskflow-stage1-cpu-r8-20261120/out/`; r8a has only the easy-nothink arm. `local_llm.py` counts `step_finish` events, enforces the worker wall timeout, and already performs a narrow same-session nudge for a no-result, unchanged worker ending in at most two steps. The census uses the recorded post-nudge outcome and the audit, rather than treating lack of a `TASKFLOW-RESULT` alone as an early-end.
