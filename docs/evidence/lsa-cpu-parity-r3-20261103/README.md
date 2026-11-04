# LSA CPU all-keys parity R3 evidence

Preserved from the 2026-11-03 approved all-only continuation against the R2 dense arm. Scope: one 45-ID prefill and 248,320 vocabulary logits, all 16 global attention layers; no speed, retrieval-quality, MI210 or full LSA-SCREEN-1 completion claim.

`RESULT.json` and `checker.json` report max absolute difference 0.0 and identical argmax 248068. `trace.jsonl` has exactly layers 3,7,...,63; each records 45 queries, 1035 allowed positions before and after, and changed=0. `preservation-check.json` independently checks the preserved compressed logits and trace offline.

The source/binary seal is `candidate-identity.json` (SHA-256 0319ffdeb8e587cfb2c26098e161f3f8aa36fc7cac904e84ce45f148cef18b4d). Logs and live mapping monitors retain binary identity evidence. `r2-candidate-identity.json` and `dense-provenance.json` bind the reused dense comparator. The current experimental qwen35.cpp has since changed and is not copied as the run source; `source-preservation.json` records that mismatch. Only source files matching the run seal are preserved under source/.

Admission provenance is retained verbatim: R3 was an owner-turn self-claim on CPUs 24-27, not a keeper-granted run (`provenance.json`). The row was unpublished after its qualification failure (`unpublished.json`, `FAIL-1.json`); no current ready manifest or granted terminal receipt was found. `spec.json` is the original proposal, not proof of a grant. Do not fabricate registration or .ended state when filing its evidence.
