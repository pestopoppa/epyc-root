# NI06 corrected recipe original custody

Original Actions run `37425524371`, attempt 1, completed successfully at recipe `1e61b4185387e786dc8da4c5e1193c968520fe02`. Exactly two jobs ran; K3 was not repeated. Root source/producer remains `ec513cbefa937bbe382ea502a88ab96c27022863`; CJ13 source remains `1721cc208d756506b7d31e315436f1edf8cb343b`.

| Job | Original native result | Executed / collected | Skips | Source bindings | Existing shared grade |
|---|---|---|---|---|---|
| Root graph | TRUE, exit 0, 64 passed, zero failure/error | 64 / 66 | 2 | 1,248 independent Git blobs + 2 runner contexts | Judged/Located, 1 row |
| CJ13 | TRUE, exit 0, 44 passed, zero failure/error | 44 / 44 | 0 | 3,324 independent Git blobs + 2 runner contexts | Judged/Located, 1 row |

Root's two skipped `LiveArtifact` tests require a generated, git-ignored `.index-graph.json` absent from the disposable checkout. They did not execute; the 64 passing cases are the bounded fixture evidence. Root's corrected recipe uses pytest 8.4.2. CJ13 uses pytest 9.1.1/jsonschema 4.25.1 and inert package shells with a noninstantiable LLMPrimitives sentinel; real class/getter branches, application package initialization and live backend schema compatibility are excluded.

Original API ZIP SHA-256 seals:

- Root graph: `f1de0044814a4622794e785a9fda13f280a24687d23de205737b6e9d44a354a5`
- CJ13: `98cd5447bf8c7a79609959d715c57a17189bc18aea598b167a2fc701ae809cae`

Independent expected source manifests were derived before reading original records from exact pinned Git trees, capture.py's literal config declaration, and Git archive blobs. Every captured source byte matched its independently pinned binding. Original execution argv, selections, repository pins, runner/run/attempt, context fields and native sidecars were strictly reopened with the existing producer; projection and grading used the existing shared adapter/grader without a new ladder. Runner pip-freeze/environment remain sealed runner assertions, not independent package-installation proof.

Complete ZIPs, source/read snapshots, environment context, original receipts/requests/JUnit remain private at `/mnt/raid0/llm/tmp/codex-ni06-kb-20261006/run-37425524371-originals`. This small public summary excludes complete private source/context bytes and cannot independently reopen receipts.

Prior run `37424571462` remains unchanged: K3 TRUE 15/15, CJ13 FALSE 23/44 passed with 21 failures, and root graph NULL for inconsistent JUnit suite counts. This corrected recipe does not rewrite those outcomes. No inference/model/reindex, whole-suite pass, retrieval quality, production performance or deployment verification is claimed. MAIN acceptance/promotion is separate.
