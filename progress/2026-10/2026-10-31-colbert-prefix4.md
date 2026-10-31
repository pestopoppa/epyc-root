# PREFIX-4 encoder contract repair — 2026-10-31

The orchestrator change landed on `main` at `7d92b1a8c198c2b3cd86e0920bc7f1c54364454f`. It fixes native PyLate preprocessing/output contract mismatches and segregates qd-v2 stores. On the unchanged 20-snippet cohort, all 44 native rows became cosine-computable. LateOn passed 22/22; Reason passed 19/22 with 3 numeric failures retained under the unchanged 0.01 threshold. The run changed no model, deployment, or index and makes no retrieval-quality or adoption claim.

Validation: 76 tracked tests passed (15 new contract tests and 61 existing consumer tests), 14 prior model-free checks passed, make gates and ruff passed. Existing qd-v1 stores refuse under the new encoder, so use requires a separate rebuild; `ROLE_NONE` legacy behavior remains supported. Existing SC50 source family was reused; no new adapter, ladder, or measurement warrant was added.

Durable evidence: [`artifacts/compute/colbert-prefix4-20261031/SUMMARY.json`](../../artifacts/compute/colbert-prefix4-20261031/SUMMARY.json) and the accompanying capsule rows, report, validation, and hashes. [belief: cc]
