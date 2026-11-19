# P2 source-derived private diagnostic — 2026-11-02

Private packet: `/mnt/raid0/llm/tmp/kv-prefix-fork/kpf26-real-siblings-20261102/` (KEEP, mode-restricted); raw source and model output are not reproduced here.

The API response reports 2 requested, 2 launched and 2 completed scouts, 0 failed. Slot sampling has 255 records, 87 errors and 134 positive samples; observed fork is slot 2, 3,293 tokens from slot 3 checkpoint. These are observations from one constructed, source-derived, unscored direct-claim case, not a paired serving or outcome gate. The supervisor exited 2 with an unexpected-EOF shell error, so this is not a clean completed-run receipt. Model and API processes were verified absent after exit. The model hash was briefly unpinned before correction; co-tenancy rules out timing claims.

Raw file SHA-256, verified 2026-11-02:

- response `d369dfa9ba927447d678b09b0007766fc51a09314f8e7e70d08cebf7fbab400e`
- slot samples `01b21e3e0607521da5ce0609c6440c64c05685ec0f523931ea6bfbe25d9d01bc`
- launcher log `b9dc6dd2519f722f34895c2ea913624401b15cab86ce81d392812cbfc3bdb504`
- server log `194bdfde5bf7dfd6452eb4ec53ef5292d6fe9382d3fab74e5bc4bc305ee9190d`
- API log `a765a6274456d2e2d24ef50393f77e777462e87f18f02855ad3fa1341a6649e2`
- exit-code file `53c234e5e8472b6ac51c1ae1cab3fe06fad053beb8ebfd8977b010655bfdd3c3`
