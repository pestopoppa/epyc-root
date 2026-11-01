# Decision-aware routing producer-stage metadata split

## Original task

This closes the `stage` / `producer_role` split box in [`handoffs/active/decision-aware-routing.md`](../../../handoffs/active/decision-aware-routing.md), preserving the original task text. The field that prices reward now identifies a real model producer when one exists; pipeline-only stages no longer masquerade as model roles.

## Implementation and publication

- Tested source commit: `3011c9e9271ecebd50892b818530f21de0e22c75` (`Split pipeline stages from producer roles in completion metadata`), based on APP main `9e138e3a3e22ecf8c57cd5bf50beed571d107b54`.
- APP publication: `da163c70cc347337f7d76d3ce5acc14fafc75411` is the merge commit on `epyc-orchestrator` `origin/main`; it includes the candidate plus the disjoint main update then current at `318284682`. The serialized publisher verified that remote main carried its HEAD and `git cherry` was empty.
- The candidate changes exactly eight files: the existing NI CI workflow; the three chat-pipeline completion emitters; and four focused test modules. The complete source diff is preserved byte-for-byte as `producer-stage-source.diff.gz`; decompress it with `gzip -dc producer-stage-source.diff.gz` or use the published APP commit.

The four pipeline sentinels (`mock`, `plan`, `stream_init`, `proactive_delegation`) are recorded in the optional `producer_stage`; their `producer_role` and `final_answer_role` are null when no model generated the completion. The proactive output is a non-model concatenation, so observed child roles remain contributor lineage and are not promoted to a singular producer. Direct model completion roles stay as observed. API `role` / `force_role`, aliases, dispatch, and historical records are unchanged. `q_reward` and its selection order are unchanged; metamorphic tests show the old and split metadata produce the same scores with and without the existing explicit `role` override.

## Hosted validation

- Workflow: [NI programmatic feedback and DTAP contracts](https://github.com/pestopoppa/epyc-orchestrator/actions/workflows/ni-code-contracts-20261101.yml)
- Original run: [41283762176](https://github.com/pestopoppa/epyc-orchestrator/actions/runs/41283762176), job `124780788850`, exact head `3011c9e9271ecebd50892b818530f21de0e22c75`.
- Conclusion: success; **399 passed, 0 failed, 0 errors, 0 skipped**, pytest exit 0, one existing `PydanticGraphDeprecationWarning`; JUnit reports 185.711 seconds.
- GitHub artifact: ID `13074765135`, name `ni-code-contracts-41283762176-1`. Its original downloaded files are retained under `original-ci-artifact/`, including source commit, 30-file SHA-256 manifest, dependency-install stdout, `pip freeze`, pytest stdout/exit code, and JUnit. `run-api.json`, `job-api.json`, and `artifact-api.json` retain the original run/job/artifact metadata.
- Each of the 30 runner manifest hashes was independently checked against the candidate commit's Git blobs: 30 matched, 0 mismatches. The raw artifact file hashes are listed in `SHA256SUMS`.
- No local runtime tests/builds were run during the C3 restriction window; no model, performance, quality, or deployment claim is made.

## Scope limits

This is completion-metadata attribution only. It does not change reward math, pricing thresholds, metric directions, request controls, historical telemetry, routing policy, model quality, or runtime deployment. No new source class, grader, or measurement ladder is introduced; the run is existing native CI source-conformance evidence.
