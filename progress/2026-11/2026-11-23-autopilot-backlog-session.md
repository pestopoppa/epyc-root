# 2026-11-23 autopilot backlog session

## HIL-EVO-CASES-1 (non-inference, docs only)

Appended items 23-26 to the HIL-2 pre-first-suite-run checklist in `docs/design/harness-improvement-loop-design-20261006.md`: (a) HookEvo in-sample retention case, (b) Life-Harness four-layer taxonomy plus trace-replay gate, (c) plugin install envelope (BEP-5 input, autopilot-program.md line 2217), (d) matched-budget rule (AP-BSV2-ACCEPT-RIGOR (e)). Sources: intake-2857#00/#01/#02/#04/#05, intake-2858#00/#02/#03/#05. Footer updated to items 7-26. No inference run.

## AP-BSV2-ACCEPT-RIGOR

Amended the BSV-2 accept design in `handoffs/active/autopilot-program.md` (R1 disjoint accept tasks, R2 fresh parent re-run, R3 sealed test split, R4 per-round decision record with status split and tokens-per-accepted-gain, R5 rollout/token budgets). Offline replay over both journal shards (`scripts/autopilot_replay/bsv2_accept_rigor_replay.py`): 130 past accepts, 0 survive all five rules (R1 0, R3 0, R2 0, R4 0, R5 1 key-name hit). AutoPilot stayed stopped; no inference run.
