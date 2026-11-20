# AK-DTREE-2 r5: FAIL(crash 27b)

FAIL(crash 27b) under prospective R5 rule: ident-27b-p0 child rc=-11, despite launcher rc=0. Decode rejects duplicate sequence position X=14/Y=14; assertion at tests/test-dtree-batch.cpp:209. No oracle counts, A3B or timing. Reported residency OK (41,782,329,344 B peak); build source e581a175d67d810518d92f0754b873e139c045bc, test SHA-256 d52c8d66aac504e503507a1dfa1968a9972740792dcc0da62966a1d08797fe91. R5 required both models but runner stopped after first failed unit: incomplete coverage cannot PASS. No kernel-cause attribution; P5 remains gated.

The width-matched control therefore supplies no rate comparison. The next experimental repair must correct the control sequence lifecycle, retain the prospective R5 thresholds, and run both models before its aggregate verdict. Parent AK-DTREE-2d stays open.

Existing evidence (no copied payloads):

- `/mnt/raid0/llm/tmp/ak-dtree-batch-identity-gpu-20261120-r5/out/results.jsonl` — SHA-256 `50eacc7f0ed8592c0e500f74e477859d921111ab3d6accc21b36a03c6c16092a`.
- `/mnt/raid0/llm/tmp/ak-dtree-batch-identity-gpu-20261120-r5/out/RESULT.json` — SHA-256 `f8969b20d0e1e9d67ee26597702f4f6a3860ac0b20cdcaeecde219512b42c9f9`.
- `/mnt/raid0/llm/tmp/ak-dtree-batch-identity-gpu-20261120-r5/SOURCE.sha256` — SHA-256 `078e6aabbbf651b4eea7734d87a11ded879860a2ac4ffefa014d3b9999e0632a`.
- `/mnt/raid0/llm/tmp/ak-dtree-batch-identity-gpu-20261120-r5/BIN.sha256` — SHA-256 `9d230a67fcf058a4628743b72afaa8baf8ec003ca30452b552ca92d541a39e32`.

R4 already has a filed FAIL receipt; acknowledging its delayed alert does not revise that verdict.

Concurrent owner filing: filing returned NOOP because the FAIL receipt already existed at 2026-11-20T02:31:40+00:00, bound to the same native-result digest above. Its answer reports the control bug fixed and a repeat underway; inspect that successor before creating duplicate repair or inference work.
