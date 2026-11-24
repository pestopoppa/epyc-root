# 2026-11-24 autopilot backlog session

## Wrap-up (operator /wrap-up)

- Landed overnight (details in `2026-11-23-autopilot-backlog-session.md`): AP-LH-WHOLE-TRAJECTORY-CAPTURE (orch `4c07ffd5`, ticked) and the AP-ALFWORLD-SUITE adapter (orch `2a04aaf7`, rebased over the capture commit with both flags kept; box open until the live 5-episode slice after AP-POSTREBOOT-ALF-SMOKE).
- STACK-UP-RELOAD-QUEUE (`harness-program.md`): sub-bullet lists every orchestrator commit since 2026-11-20 that the next API-only reload ships (sampler tap, BSV-2 gate, distill, capture, ALFWorld suite). The capture flag needs the API side on too.
- Checks: index --check rc=0; belief ledger fresh (lag 0); no prune candidates. Research README still 60 days stale: waiting on the operator's manual fix of the broken `../../MEASUREMENT.md` link (Edit hook 20 refuses every edit to that README while that link is broken).
- Open operator choice: ALFWorld slice inside or outside autopilot's keep/revert aggregate (built outside).
