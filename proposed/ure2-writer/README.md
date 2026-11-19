# URE-2 live escalation writer candidate

`implementation.patch` adds a live approval writer and unit tests to
`epyc-orchestrator` at `c1df9962c919562ce02bebb5608451093fe6bf6c`.
It has **not** been applied or landed in that repository. URE-2-writer stays
open until application and validation there. The dispatcher currently permits
edits only in this root lane; application needs authorization for an isolated
orchestrator worktree. No production source, process, feature or era changed.

The shared quality helper writes once per attempted target, covering direct
`/chat`, ReAct and opt-in `/v1`. Rendering a `/v1` receipt does not write again.
Both graph engines share the graph transition hook; the two streaming paths
record their own role transitions. Graph writes work without a progress logger.
Parked targets, backend exceptions, empty replies and in-band errors remain
distinguishable. Two attempts with identical request/target remain two records.

Each approval links a partial behavior signature in the existing shared store.
The pair commits atomically despite the legacy insert helpers' internal commits;
an injected second-insert failure leaves neither row. Persistence failures log
a warning and preserve the response/fallback behavior. Prompt/answer hashes
avoid retaining their raw contents. Model identity comes from the registry when
available; absent quality/uncertainty evidence remains NULL. System approval
does not claim human governance or task success. Decision-time graph/stream
outcomes explicitly say `selected_pending_execution`; re-answer outcomes describe
the generation attempt. These are not calibrated quality judgments.

Validation on 2026-11-19:

- **160 passed**: 11 new tests plus existing `test_v1_escalation.py`,
  `test_graph_observability.py`, `test_stream_adapter.py`,
  `test_chat_pipeline_stages.py`, and `test_gpu_window_parked_role.py`.
- The new HTTP `/chat` test stubs the handler's routing/inference setup but runs
  the real direct stage and quality helper: two model calls, one approval,
  non-null behavior-signature link. No inference or network model call.
- `test_v1_escalation_off_golden.py`: **8 failed on candidate and baseline**.
  Both reproduce the old expected usage versus current unknown-usage fields.
  This suite is not claimed green and its fixtures were not regenerated.
- Ruff passed under both root and application settings for the writer/tests;
  all eight candidate files compiled; `git apply --check` passed on the pinned
  application checkout.

Source impact is six existing modules, one new writer and one new test module.
Manual call-site review found one shared quality-attempt hook, the graph hook,
and four streaming transition hooks. Risk includes synchronous SQLite persistence
on the serving path; latency impact has not been measured. GitNexus status was
stale and impact queries returned no indexed repositories; no graph-based blast
radius claim is made and the external index was not modified.

Rebuild the reviewable patch, then test without modifying the application tree:

```bash
python3 proposed/ure2-writer/candidate.py
PYTHONDONTWRITEBYTECODE=1 \
  /mnt/raid0/llm/tmp/routing-intelligence/ure2-writer/venv/bin/python \
  proposed/ure2-writer/run_tests.py
```

`candidate.py` reads the six modified source modules using `git show` at the
pinned commit and imports the candidate in memory. It does not materialize a
source checkout. `run_tests.py --baseline <test paths>` imports their unchanged
pinned versions for comparison. SQLite files, pytest cache and the isolated
test environment live under `/mnt/raid0/llm/tmp/routing-intelligence/ure2-writer`.
That environment references the existing application dependency directory and
adds pytest 9.2.0, pytest-asyncio 1.5.0 and Ruff 0.17.5. Recreate it if scratch is
reclaimed; no source-tree scratch or copied upstream logs are required.

After source-worktree authorization, apply the patch to an isolated application
worktree based on the pinned commit (or review/rebase the patch against its new
tip), run the included `tests/unit/test_live_escalation_records.py` and the
named regression suites against the actual patched files, then land through
that repository's approved workflow. Only then complete the handoff box.
