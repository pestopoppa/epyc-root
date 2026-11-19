# 2026-11-17 — pipeline-mgmt

## Compute (rowflow keeper)
- Keeper kept placing all day; all four CPU quarters busy most of the day (inf86 x3, wrap8, c12-cpu-validate, WRAP-5 repro).
- GPU idle 12:45–13:46Z: `inf75-c12-w3-halfb-census-20261117` (needs gpu-quiet+q2+q3; operator-registered placement includes MI210 host threads) put the keeper in DRAIN until 18:33Z. AutoKernel republished it as r2 at rank 90; the drain dropped on the next pass. Then fa-bugfix was blocked by a c88-95 claim inside busy q3; AutoKernel republished all six GPU rows as `mi210_0,184-191`. First GPU grant 13:46Z (fa-bugfix-r2).
- GPU rows completed and filed by AutoKernel: fa-bugfix r2, asm-aiter r2 (pass: topksoftmax 8.4x, i8gemm 1.5x), mmq-h10b r3 (pass), c6 r6 (inconclusive), farows r13, W3 r2 (pass), MoE-Spec confirm.
- "Rows vanished" report: false alarm — rows finished, AutoKernel's watcher missed them (fixed on its side). Keeper reap events touch only tmp/ run dirs.
- `inf75-c12-w5s-census` enrollment refusal: not a sha mismatch (matches dry run); row declared shape quarter with regions 0-95. Routed to AutoKernel.
- llama-server build rows failed on the newer source's web UI download (`tools/ui ui-assets.cmake:291`, rows have no network). AutoKernel vendors the offline `tools/ui/dist` at extract and is republishing every build row.
- WRAP-5: not reproducible as a crash (gguf example read mode asserts by design on real models); no upstream post.

## Handoff dispatcher
- Relaunched at small width (max_live 2): deployed missing `token_guards.py` / `codex_budget_meter.py` into `compute-flags/bin`.
- Root cause of "Codex credits still 100%": both sessions resumed their 98–117M-token threads; the G2 token ceiling (15M) killed them within 60 s at 11:00Z and again at 19:34Z after an unpark. Event-path resumes ignore `fresh_next` (bug HS-FRESHNEXT-EVENT-RESUME). Only real work: one turn each (alert acks, KVQ fix prep, R7 evidence archive).
- D9-acked fix in progress on `pm/freshnext-20261117`; existing dispatcher test file was already broken on origin/main (HS-TESTS-ROT), being repaired before landing. Both sessions parked meanwhile (no token spend).

## Filed boxes (churn-pipeline.md, 2026-11-17 findings)
2 ticked (HS-SMALLWIDTH-RELAUNCH, ROW-SHAPE-W5S), 5 new open (HS-FRESHNEXT-EVENT-RESUME, HS-TESTS-ROT, KEEPER-DRAIN-HOLDS-GPU, KEEPER-REAP-INLINE, KEEPER-FAST-COMPLETE-FLAG). The three keeper items need operator D9 acks.

## Deferred (named blockers)
- E5 Stage-B r6: waits on operator host reboot (uptime gate).
- Keeper fixes: each needs an operator D9 ack.
- `/mnt/raid0/llm/worktrees/noninf-20260924/` removal: needs operator OK.
