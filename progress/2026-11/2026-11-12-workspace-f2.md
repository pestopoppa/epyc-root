# 2026-11-12 — workspace-f2

## Wrap-up (operator-invoked) — agent-file compression v3c/v3d and deploy wiring

1. **AFC-V3C-PROD-TOOLS DONE (Q38 half).** All four Flash-Next rows filed. none 0.785/0.600/0.927. Paired lower bounds (comp/proc/recall): mild −0.080/−0.017/−0.050; medium −0.081/−0.040/−0.048; aggressive −0.029/−0.041/−0.069. All KEEP; operating point **aggressive** for both models on production tools. none-r2 republished at rank 20; mild-r2 republished after a HARD-END-CAP drain cut (Pipeline fixed same-id requeue for admission caps in 3c4d2c4b5).
2. **Deploy ownership.** A read-only trace found no production path gave local models any agent file (`agent_file_compression_operating_point` was validated, never applied). Operator decision 2026-11-12: wire it for worker_general and architect_general. Code landed on epyc-orchestrator 440ed243c behind `agent_file_injection` (default OFF). Side finding: architect_general's old aggressive value came from the retired Qwen3.5-122B; v3c re-backs it. Fixed `/new-model` Step 6.5 text (`.claude/commands/new-model.md:219`), which claimed the orchestrator routed models to a compression level.
3. **AFC-Q36-AGENTFILE-CTX-REFUSAL (reword) in flight.** New "Requests That Conflict With These Standards" section appended to the aggressive variant (row code dirs only). Q36 row filed: 0.787/0.687/0.973; vs v3c aggressive compliance d=+0.220, LB +0.1525; procedure LB −0.034; recall LB +0.007; vs none every LB > −0.10. Caveat: verbatim-quote directive overlaps the clause-cite scorer. Q38 reword row still running; box open, next step boxed (land directive + regenerate variants if Q38 passes).

**Row-scheduling lessons.**
- Rank decides placement: a rank-100 row never places behind a rank-25 whole-host row; the Q38 none row waited ~10 h unplaced at rank 100.
- A drain-cap cut is now requeued under the same id for both CAPCUT and HARD-END-CAP (3c4d2c4b5).

| Repo | Files |
|---|---|
| epyc-root | `handoffs/active/engineering-hygiene-backlog.md`, `.claude/commands/new-model.md`, this file |
| epyc-orchestrator | 440ed243c (landed earlier) |
