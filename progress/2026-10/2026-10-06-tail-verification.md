# Tail verification preparation — 2026-10-06

Prepared the ROOT-only read-only verifier in `/mnt/raid0/llm/tmp/intake-reverify/final-verification-tail-proposed`, protected by KEEP. Main approved input binding SHA-256 `278c4b5fb32e0f8d8aacf78f3374a72ee35935920f2c6de3b216192a681b9738`.

The bound canonical snapshot has SHA-256 `5e58077522074a459a1300b3d4100a631bd331167f6d08819bf26c8c74d3146a` and 14,341 frames. The verifier preserves the original 13,891-frame prefix plus the exact 420 reviewed frames and analyzes the 30 peer suffix frames separately. Original application and zero-append-retry receipts retain custody of the original reviewed ledger; they are not relabeled as current-ledger receipts. The original full13 dependency impact audit remains the isolated base-versus-base-plus-420 audit at `2026-10-06T11:52:22Z`.

The fresh current index has SHA-256 `c63611077e16aeba9bec497b7aee7208572ab63b96a9752f6e6f7004acfe5332`; clerk inspection found the exact original reviewed candidate bytes preserved followed by 42,649 peer suffix bytes. The verifier binds current docs/code/index and refuses drift, protected direct science interference, or failure of an actual required gate.

The ROOT job includes exactly `test_repeated_cleanup_preserves_live_sibling_marker_and_directory_keep` and `test_orphan_sibling_marker_still_trashed` before current gates. Their result receipt will be written from actual execution, with the reviewed cleanup source/test hashes. No all29 repeat is requested.

Preparation checks were Python AST syntax, shell syntax, JSON parsing, and byte/hash inspection only. This preparation session executed no fold, gate, test, materialization, replay, retry, or ledger write.

Main reports the admitted ROOT verification-only job is durably queued with captured PID `1071338`, behind CPU queue owner `q1` / `jetlong-small`. Scope has no interphase wait. At this checkpoint no tests or current gates have executed and no passing current-gate outcome is claimed. Original input bindings must remain unchanged after launch; later publication/document changes require a new binding namespace and separately bound final verification.
