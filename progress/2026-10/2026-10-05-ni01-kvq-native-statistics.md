# NI05-01 — KVQ native statistics compatibility

MAIN accepted the paired implementation after [NI05 third run 37280071522](https://github.com/pestopoppa/epyc-root/actions/runs/37280071522) passed 18/18 root adapter cases and 15/15 research ingest cases, with zero failures or skips in those selections.

The root adapter accepts the producer's original `{n, median, mad}` statistic records when the median is finite, retains the original records, and rejects malformed/nonfinite statistics. It continues to distinguish K and V and preserves the producer's flash-attention, benchmark-surface and depth cautions. No measurement ladder or producer schema was changed.

Research source `e98909009f5dd2d148ad0e93029ea9fb85ba031f` removes only the obsolete strict xfail for `test_the_producers_native_summary_shape_is_ingestable`. Its adjacent obsolete rejection test now supplies an actually malformed native statistic (missing median, with producer-authored row digest recomputed) and checks refusal before any ledger append. The actual research suite executed against root `36c191832bd58f175f0a7b90e733f2ea14a5169b` and passed all 15 cases.

The third research execution sealed an original native CI receipt with 15 collected/executed/passed cases and `fixture_execution_conformant=true`, plus original request/log/JUnit/readset sidecars, before artifact upload. Evidence is retained in `/mnt/raid0/llm/worktrees/codex-ni05-validation-root-third-20261005/ni05-third-artifacts/research-results/native-kvq/`.

The first two campaign runs remain plain validation. No sweep, inference, new measurement/model/kernel claim or historical backfill occurred. VB-KVQ-V10-DICT is satisfied; VB-KVQ-V10-INGEST still requires the owning session's new complete post-hook sidecar and recorded fold/planner checks; no inference producer is scheduled by this session.
