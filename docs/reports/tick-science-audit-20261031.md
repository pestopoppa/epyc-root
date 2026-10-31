# Handoff tick/deletion science audit, 2026-10-30T00:00Z..2026-10-31T19:47Z

Opus-high subagent of workspace-58, operator request ("tasks ticked without science shouldn't be allowed to be hidden/stashed away").
Scope: 324 non-merge commits touching handoffs/ on origin/main up to 4288356f0, plus the 52 merges checked with --cc.

## Ticks: 264 added [x]

| session | SCIENCE | NON-RESULT | UNSUPPORTED | FALSE-RESULT | DECLINED-AS-TICK | total | born-ticked |
|---|---|---|---|---|---|---|---|
| NI | 8 | 39 | 0 | 5 | 0 | 52 | 1 |
| refactor | 7 | 108 | 2 | 0 | 0 | 117 | 52 |
| codex3 | 17 | 54 | 1 | 0 | 0 | 72 | 19 |
| ws58 | 1 | 8 | 0 | 0 | 1 | 10 | 6 |
| other | 4 | 9 | 0 | 0 | 0 | 13 | 1 |

### Bad ticks still [x] when audited
- F4 (NI) colbert-reranker-web-research.md PREFIX-3, commit 29c522243: ticked on a nonterminal run (22/22 contract mismatch, cosine unknown).
- F5 (NI, contested) speculative-decoding-mtp-refresh.md INF-50-GNX-R3-T1-REQUAL, commit 3dca1d4d2: ticked 7 min before its receipt landed as FAILED-RUN rc1 (missing --complete-cmd; 37/37 returns preserved). The receipt class was never amended.
- U3 (refactor) yarn-context-extension-research.md S0-V34-LOCK-LOSS-REPRODUCER, commit 2a50a877d: [belief: cc] with no SHA, artifact, test or receipt anywhere.
- D1 (ws58) architect-model-selection-bench.md Qwen3.6-35B IQ3_XXS: an operator decline rendered as [x]. Fixed in this commit as a non-checkbox declined line.

### Already reopened inside the window
F1/F2 GPU-ZOS-2.2 (NI; FAILED-RUN build, exact rule NOT MET), F3 NEMO-PROF-RESEG (NI; done-criterion unproved), U1 AK-PM-12 (codex3; no producer wired), U2 (Z) log retention (refactor; legacy-only edit).

## Removed open work: 0 vanished
- 25 `- [ ]` deletions: 21 were ticked in the same commit, and 4 are still open at HEAD.
- One identity rewrite: 479595265 (refactor) autopilot-continuous-optimization.md: the UNOWNED scorer-defect task became a repair tick, and the original text survives only in completed/.
- 8 index rows were deleted, and all were re-added in the same commit. No handoff file was moved or deleted.

## Watch list
- 79 born-ticked [x] lines (mostly prep that says "parent remains open") inflate the done count.
- 24 ticks cite evidence only under /mnt/raid0/llm/tmp.
- 4 refactor "qualified launcher" ticks whose runs then failed (ufh12-r1-irt-r2, R18-A, hil15-s2-unknown-resume-v3, HIL15-S0-V11).

## Proposed structural gate (LOOP-50)
New scripts/handoffs/belief_capture_check.py (~200 lines), wired as a blocking line in scripts/hooks/pre-commit.extras (receipts are host-only, so CI cannot see them), with a --range A..B replay mode:
1. An added [x] whose cited run's latest .FILED is FAILED/INCONCLUSIVE/INCOMPLETE/PARTIAL/rc!=0, with no later FINAL/COMPLETE, is refused unless the line carries `[receipt-ack: <id> <CLASS> — reason]`. A [belief:] tick citing a run with no .FILED yet is refused.
2. A tick whose own line says unknown completion / INCONCLUSIVE / NOT MET / no verdict is refused.
3. A [belief:] tick with no SHA and no git path is refused.
4. A removed `- [ ]` is refused unless it is re-added (ID or first 40 normalized chars), `[moved: <path>]`, or `[declined: <who/date> <reason>]`; a decline is never [x].
5. Index rows are already covered by index_state.py --check coverage.
Backtest: catches F1, F4, F5, U3 and the identity rewrite; misses F3, U1 and U2 (scope judgments, which stay with the daily audit); about 2 false positives; under 1 s per commit.
