# 2026-10-24 — Codex non-inference Vidya source scope

## EVL-47 — `VB-DS41-1017-AKSCOPE.SRC`

- Corrected the DS41-1017 ROOT adapter scope: the native producer binds each exact model artifact and CPU backend but does not record a whole-model census quant. The reader now omits `quant` rather than treating arm labels as census values.
- Added strict adapter checks tying each arm to its expected artifact path and pinned identity. Added tests for both arms, valid-hash path alias refusal, and projection through the actual loop-belief matcher: correct CPU target accepted, wrong model/backend rejected, and explicit quant mismatch remains filtered.
- Actual 1017 tensor census from the retained W5a native manifest: Q8_0 is dominant (321 tensors; MXFP4 120). A current Sept-Q4 GGUF is absent, so no Sept census value was inferred. The canonical ledger contains no `ds41-1017-validation` source frames; no correction replay or ledger write was needed.
- Focused region-locked tests: 10 passed. No ladder, producer, source class, source-table row, ledger, planner, kernel, or runtime changes.
- The parent `VB-DS41-1017-AKSCOPE` remains open: shared research clone already has the native producer and W5 sidecar; remaining work is inspect ABA capture coverage without manufacturing retroactive tuples and review a scratch-ledger dry-run of existing W5 rows. Canonical ingestion waits for adapter integration and main approval.
- Scratch-ledger dry-run is queued under the required CPU region lock; q1 was held at the time of waiting.
