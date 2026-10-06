# NI06 original bounded fixture custody

MAIN accepted NI06-03 K3 source candidate `9d3a338acdd3dec258afee27ac3d359dc35efbf3` after reviewing the original native K3 result and independently verifying its captured source bindings. This is bounded synthetic fixture conformance. Promotion is separately MAIN-owned.

Original GitHub Actions run `37424571462`, attempt 1, recipe `fd57cf7780902ae1a7f5b022626d4529c84c3895`, producer/root `ec513cbefa937bbe382ea502a88ab96c27022863`:

| Original job | Native outcome | Counts | Existing shared projection |
|---|---|---|---|
| K3 | TRUE | 15 passed / 15 executed; zero failure/error/skip | 1 row, Judged/Located |
| CJ13 | FALSE | 23 passed, 21 failed / 44 executed; zero error/skip | 1 row, Judged/Located |
| Root graph | NULL | Native summary unknown: inconsistent JUnit suite counts | 0 rows |

CJ13 APP pin is `1721cc208d756506b7d31e315436f1edf8cb343b`. The original false/null records remain unchanged; K3 acceptance does not accept the other jobs. Shared grades are observations without protocol citation, not retrieval-quality or production-performance measurements.

Original API ZIP SHA-256 seals:

| Artifact | SHA-256 |
|---|---|
| `ni06-k3-37424571462-1.zip` | `d9aad80a26d803e01127b12758d1aced603b7f0f16334c7f234a92daaa4cfae5` |
| `ni06-cj13-37424571462-1.zip` | `13886cc8f89a6f404669a34169537f32c3a6baf5a60e5bf365f92b311480cb7e` |
| `ni06-root-graph-37424571462-1.zip` | `c1fb58a7f10ee6821ce0badb0a9f42624e238121ca81ed14f1c26996bf4d8682` |

The independent K3 review matched all 3,325 Git source bindings against exact pinned Git blobs: root 623, recipe 625, APP 2,077. Two additional original runner-context records bring the exact native readset to 3,327. Those context records preserve pip-freeze and declared environment bytes; they are runner assertions, not independent proof of package installation. Receipt file SHA-256 is `e244afb488702472e9d71f299824643f98883aefb9d89fafef5d44403c361708`; embedded receipt self-hash is separately `8aab5a8f3a786cf85b645edccae000feed2dfeb9790fd9720662e96b93cb0d0c`.

Complete original ZIPs, captured source/readset snapshots, runner context, original native receipts, execution requests and JUnit remain private at `/mnt/raid0/llm/tmp/codex-ni06-kb-20261006/run-37424571462-originals`. This small public summary excludes full original source/context bytes and cannot independently reopen native receipts. Seals and counts do not substitute for those private originals.

No inference/model/embedding calls, stored-corpus reindex, retrieval improvement, production deployment verification, or whole-suite pass is claimed.
