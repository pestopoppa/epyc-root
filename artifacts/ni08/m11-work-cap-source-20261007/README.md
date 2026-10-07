# Memory work-payload cap source acceptance — 2026-10-07

An oversized prefix could forge the sanitizer's existing truncation suffix and escape the nominal cap, including the redaction scanner's input limit. The fix trusts a same-cap marker only after a bounded prefix and bounds decimal metadata to 20 ASCII digits. Legitimate second-pass idempotence, objective text and existing item/redaction policy are preserved.

Source APP `926d90c95ca452636d59b7edd343abd8bcae81d2` is merged and pushed at `31185ca59628aaa43d39ed08b5f88ffaa2af0181`. Recipe ROOT `9f0714a71e9c4e45fdbba1d4652f334915125fa1`, pre-enrolled context `0da62ca1cb484f54f0e58dc514f10cd61b9ac001`, unchanged native carrier `4c0c653baf1654c8c25c66433cf39c8faefd8e52`.

[Original hosted run](https://github.com/pestopoppa/epyc-root/actions/runs/37564914928) executed and passed all 41 controls with zero failure/error/skip. Native conformance TRUE; existing shared grade Judged/Located. MAIN independently authenticated artifact 11457782712 and its complete ZIP: SHA-256 `78212b4f43e8d70a02f26155ddef7465a271c227b229e0e85a6f7c692974e3e0`, 14,331,231 bytes, 2,849 members. All 2,835 Git input blobs plus three generated inputs, exact AST case identities, original receipt seal and full fresh result/source custody before/after grading matched. Forty-nine APP-locked packages retain all 783 wheel hashes.

This closes M11-WORK-CAP-SOURCE and VB-M11-WORK-CAP-CONFORMANCE only. Temporary SQLite/FAISS and fake embeddings are synthetic fixtures. No shared-host project execution, inference, live-store migration, traffic-prevalence, privacy or semantic-quality claim. MAIN did not rerun fixtures or grading locally.
