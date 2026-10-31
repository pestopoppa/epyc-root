# Accepted NI batch — 2026-10-31

This packet preserves MAIN-reviewed source and original evidence for three engineering tasks, one static artifact task and one existing-test reconciliation. Original handoff closure is applied by MAIN; this packet does not create extra result boxes. No kernel change, build, deployment, live park or inference is claimed.

## M-17e content vector repair

APP `def3e2c08dbe5939ecbbc3e4c862f6110f29fda3` adds single-row position-preserving repair with bidirectional SQLite/id_map/FAISS checks, float64 normalization, backup/atomic replacement and actual no-fallback controls. Seventeen native FAISS/SQLite/NumPy tests passed; ruff and make gates receipts are retained in [m17](m17/CAPSULE-DRAFT.md). Future apply requires stopped API/cached readers. Tests used temporary stores only. [no-belief: tooling-repair]

## Judge method exposure

APP `fb127bf0206bd6f038ffd227e0499ed4d98ecedc` adds an offline bounded inventory/report. Nine tests passed. Pool declared-input method labels: 3,541/76,704 = 4.6164%; retained historical T1 core batch: 1/45 = 2.2222%. Neither measures current live judge calls or performance. Identity scope, input hashes, full-batch completeness and task_failed/error denominator handling are preserved in [producer capsule](judge/CAPSULE.txt) and native report copies. APP durable reports are `orchestration/reports/judge_exposure_20261031/{pool_inventory,retained_t1_batch}.json`. Prospective source projection and planning-context canary remain unchecked; the existing grading ladder is unchanged. [belief: cc]

## C++ patch artifact

Research generator `e95a9d2e25c3eeedc7a6f997e608d9bd338cbc31` regenerates [test-backend-ops-cpu-fa-longctx-v1.patch](cpp/test-backend-ops-cpu-fa-longctx-v1.patch), SHA256 `395e5bbdd66f585dad4f233dfb2b57c1c0e882487244011d9d6ad39be24e0871`. This equals the archived 20261007 bytes; the previously named 20261004 directory was absent. [Verification](cpp/VERIFICATION.log) proves apply-check against declared base `4348de400191c0b4c5127047037bf9ad83da19b6` / blob `46b556039d27a3a6048d87a807d8c99e16d1049d`, reproduction of reviewed target blob `8b2991747a0f37b6b5a859e7a4da4fb879a8ee0f`, and 35 cases. No C++ build, runtime, real-mask validation or neighboring-parent completion. [no-belief: static artifact regeneration/application only]

## E3 existing test task reconciliation

Existing APP SCORE-07 `b5da2080824e56fbdccc3dd38aac2ad6a31f04bc`, TEST-2/SG-7 `ade26db3a9bda9b95500bc0f070ab929300fcffb`, RLVR-2/import `4e9efe3285dca6c44ef57f642971616d7b3ad9ef`, and QID-1 `ef0f3f21df39559acd36516e0c2d780f61a5651d` resolve the original E3 remainder. [Targeted reconciliation](e3/e3-reconciliation.log): 194 tests passed, including all 159/58 golden corpus pins, ECE-era pin, module identity, gate branches, MAD and RLVR tier checks. This records existing source completion, not new engineering output; the already-checked E3/A4 child remains unchanged. [belief: cc]

## GPU window park documentation

APP `c7d573c2661dc90aa83494d2b3f9e680742cf1d1` clarifies help/module documentation and writes successful-park warning to stderr. [Landing](park/LANDING-RECEIPT.json), 92 existing tests, make gates and [real temporary-window CLI capture](park/cli-capture-receipt.json) retained. JSON stdout stays unchanged. Manual park writes a file; server stopping requires executor open with schedule entry and grant. AKX-ALL-15a explanatory paragraph is updated without ticking its parent. No live park or server operation. [no-belief: documentation-and-cli-message-repair]

## Boundaries

Prior ROOT `4d50e71c41a115ad5605b8064cdd90c9e4fdaee9` batch (four original tasks plus five metadata repairs) is already published and receives no duplicate credit. R7 ZOS qualification remains a separate waiting packet; no floor-restoration claim. READY/model/raw/pinned lanes and previous C3 run filing remain intact. Static documentation/artifact packaging changes no application call graph. GitNexus private ROOT is unindexed; canonical ROOT is stale, and newly added APP `judge_exposure` is absent from its stale index; accepted source-review blast assessments are retained in producer capsules, with no new source edits here.
