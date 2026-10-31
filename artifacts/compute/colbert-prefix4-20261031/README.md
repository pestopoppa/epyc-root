# PREFIX-4 landed contract repair

APP main `7d92b1a8c198c2b3cd86e0920bc7f1c54364454f`; encoder SHA-256 `ae9ae18481eb64e7c2bd022c86cb396524ef4ecd0946318be1e424107e212492`.

Native44/44 cosine computable; Reason19PASS/3NUMERIC_FAIL, LateOn22PASS. Original threshold<=0.01 unchanged. Native20-snippet cohort/reference/models unchanged. All feeds, masks, output positions and shapes match before numerics. No model change, deployment, index rebuild or retrieval-quality claim.

Tracked tests76pass (15new native-contract tests+61existing consumer tests); prior14model-free checks pass. Existing test overlay uses pinned Python3.12 and existing pure-Python pytest; plugin autoload/root conftest disabled, one asyncio_mode config warning retained in TESTS.log, zero skipped tests. make gates and explicit ruff checks pass. Normal commit hooks and serialized push passed.

qd-v2 isolates changed prefix/output semantics. Existing qd-v1 stores explicitly refuse under the new encoder; separate rebuild needed before using those stores. ROLE_NONE legacy behavior preserved. No production config/index was modified.

Raw arrays, source/runtime pins and original bad baseline stay KEEP-retained at `/mnt/raid0/llm/tmp/codex-ni-prefix4-contract-20261031` until durable capsule accepted. NATIVE-ROWS retains every denominator and per-position token/mask contract. Existing SC50 source family reused; no new measurement warrant/adapter/canary completion claimed.
