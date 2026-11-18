# 2026-11-18 autopilot-backlog-session

## CODEMODE-AB probe results (35B + 27B)

- 35B-A3B (stop-on-answer n50, descriptive interim): code mode loses to direct calls (success 0.10 vs 0.43, p=1.2e-4) at ~20x fewer tokens; per-request top-8 tool selection beats static list+list_tools (0.38 vs 0.10, both C1 embed and C2 Jev oneshot); C1 ~ C2 (C2 recall 0.65 vs 0.45).
- 27B (complete, 264 eps): code mode 0.03 vs direct 0.30 (p=4e-5); selector arms floor-bound, inconclusive.
- Verdicts: /mnt/raid0/llm/tmp/codemode-ab-20261117/out/{35b,27b}/verdict.json (score.py 2c8490e3).
- Results committed as 3fcc9a711 (cited, not re-described).

## REPL containment hardening (epyc-orchestrator, pushed)

- Pushed to main: 1145b9ce..e5b95640. Adds untrusted tool-text labelling and capping, regeneration cap of 8, write dedupe, per-snippet tool-call budget, unswallowable deadline, memory-bomb refusal, and rewriting of bare-except handlers.
- Strict containment flag stays OFF: 4 tests fail with it on (follow-up).
- Follow-up ce631d31 (pushed): tool-call budget default raised 100 -> 1000 because 100 truncated code-mode batch loops; caught by a side agent.
- Shared orchestrator clone fast-forwarded to ce631d31. API is down, so no reload; the next start picks the changes up.
- Handoffs: D-RI-CONTAIN left unticked (partial; no child/cgroup lane yet), child tasks D-RI-CONTAIN-T1/T2 added in memory-program.md. UFH-01 index Next-action now points at CM-2..CM-5.

## Open follow-ups

- Fix the 4 containment-flag tests (D-RI-CONTAIN-T1).
- Branch probe/codemode-ab (selector code, off by default) is unpushed; base for CM-2..CM-5 per-request tool selection on direct calls.
- score.py labels p=1.0 ties as X_better/Y_better; quirk to fix.
- LiteParse figure boxes need PyMuPDF.
- vidya sync for intake-2675..2693.
