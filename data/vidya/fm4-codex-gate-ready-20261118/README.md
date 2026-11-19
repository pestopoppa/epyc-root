# FM-4 Codex selected-gate readiness

This prospective CPU row checks whether an independently selected regression gate for the current Codex implementation child binds its exact native dispatch and surfaces the same acceptance through the shared `coordination.fm4` reader. Its machine rule requires one selected gate, one passing execution, zero refusals and zero task-outcome claims. The reader must return the exact digest-bound `Judged/Located` harness observation, exclude it from `autokernel.planner` and retain a null task outcome.

Publisher smoke and official execution each run the four pinned suites through `run_gate.py` from the detached candidate source. Each uses four CPUs from the actual allocator grant, a separate run directory, isolated pytest temp and cache directories, and the earlier of the grant deadline and 300 seconds. A refusal preserves a partial UNKNOWN result. Completion rechecks the durable result and gate evidence.

The launcher seals the job and the owning main's private source pin manifest. The manifest seals the candidate source closure and the two read-only native snapshots. Private transcripts and raw execution evidence stay in scratch. The gate covers the implementation child's structural behavior. Historical task outcomes, oracle accuracy and Claude oracle verdicts are outside this check. The packet requires no D9 API change.

Publisher smoke **PASS** at17:33:21Z on CPUs116–119, rc0. Exactly one fresh selected-gate observation reached coordination.fm4, with one passing gate, zero refusals and zero task-outcome claims. This is prospective software/native-smoke readiness; official native acceptance, genuine coordinator adoption and Claude oracle acceptance remain separate. The original first publication queued the smoke; an immediate request was refused because that same smoke was in flight, and its original PASS is retained without rerunning it.

The original gate ran100 tests successfully with2 skips for the pending Claude D9 API. Shared-carrier checks covered14 tuples with zero violations. The private source and original native rollouts remain under the row scratch root; no private transcript text is committed.
