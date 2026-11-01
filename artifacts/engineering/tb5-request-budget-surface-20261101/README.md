# TB-5 request budget surface — 2026-11-01

Orchestrator implementation `2b9e710de2d5e183c790523c72dbbeca117e8a16` is published on `origin/main` at that commit. It exposes existing per-request `max_tokens` and `reasoning_budget` routing output for the existing assessed-task path. The caller's explicit values win; generation is capped to the admission reserve. Opt-in defaults remain empty, and scoped `ContextVar`/cache state avoids changing flags-off, zero-prefill, non-chat, or unrelated request behavior.

## Verification

- 55 focused controls passed in 7.20 s; Ruff and scoped diff checks passed. Overall R6 wrapper elapsed 12.42 s; sampled peak process-tree RSS 237,670,400 bytes.
- R6 receipt: `receipts/R6-RECEIPT.json`; captured log: `logs/focused-tests.log`.
- Receipt SHA-256: `ef788316f8ba542b7d94e8fe01932d9f073a4f7297127f1c1b6d184b81efd22f`.
- Log SHA-256: `30d4ac3c56456ef4964f53def76030877ea236773858560cbc2712fe9fd55068`.
- Source closure contains the exact 12 implementation/test paths and their SHA-256 values in the receipt. Main reviewed the current 24-caller graph directly after the GitNexus `CRITICAL_real_call` result; no model presets, native/API deployment, provider defaults, or role/deployment changes were included.

[no-belief: implementation and deterministic software controls; no measurement or production behavior claim]
