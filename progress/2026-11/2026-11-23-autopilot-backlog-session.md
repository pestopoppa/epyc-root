# 2026-11-23 autopilot backlog session

## HIL-EVO-CASES-1 (non-inference, docs only)

Appended items 23-26 to the HIL-2 pre-first-suite-run checklist in `docs/design/harness-improvement-loop-design-20261006.md`: (a) HookEvo in-sample retention case, (b) Life-Harness four-layer taxonomy plus trace-replay gate, (c) plugin install envelope (BEP-5 input, autopilot-program.md line 2217), (d) matched-budget rule (AP-BSV2-ACCEPT-RIGOR (e)). Sources: intake-2857#00/#01/#02/#04/#05, intake-2858#00/#02/#03/#05. Footer updated to items 7-26. No inference run.

## AP-BSV2-ACCEPT-RIGOR

Amended the BSV-2 accept design in `handoffs/active/autopilot-program.md` (R1 disjoint accept tasks, R2 fresh parent re-run, R3 sealed test split, R4 per-round decision record with status split and tokens-per-accepted-gain, R5 rollout/token budgets). Offline replay over both journal shards (`scripts/autopilot_replay/bsv2_accept_rigor_replay.py`): 130 past accepts, 0 survive all five rules (R1 0, R3 0, R2 0, R4 0, R5 1 key-name hit). AutoPilot stayed stopped; no inference run.

## KV-EVICT-COST-1 build phase (ak1123)

- Built the read-only evict-cost probe and the 20-cut smoke harness in epyc-orchestrator (branch `ak1123/kv-evict-cost-probe`, worktree `/mnt/raid0/llm/worktrees/ak1123-kvevict`): `scripts/autopilot/kv_evict_cost.py`, `scripts/autopilot/kv_evict_cost_smoke.py`, `tests/unit/test_kv_evict_cost.py` (12 fake-only tests pass).
- Predicts re-prefilled tokens = T' - p* and seconds = a + b*cells, classifies alignment, and marks hybrid/recurrent models cannot_shift.
- Not run against any server. Box stays unticked: smoke (k/20, pass >= 19) and the MI210 plus CPU-quarter device table are pending.

## TOC-SUPERSEDE-1 offline supersession replay (partial)

Built `scripts/analysis/toc_supersede_replay.py` (+12 tests) and replayed 78 Claude Code transcripts and 61
architect-bench bash-loop trajectories (manifest digest `18b94214...d86c53`, 139 files, 5 CPU-seconds).
Candidate share of history: Claude Code primary 0.74%, worktree/tmp 0.0%, bench loop 23.8%, pooled 1.2%.
The 15% gate is split (pooled/Claude Code under, autonomous-loop proxy over); M2 not opened. No recorded REPL
transcript with tool-output text exists. AgentDiet `artifact.zip` downloaded and md5-verified to
`/mnt/raid0/llm/tmp/ak1123-agentdiet/dl/`; `trajs.7z` extraction was refused by the permission classifier and
not retried, so that class is unreplayed. Box left open with a checkpoint. Details:
`docs/reports/toc-supersede-1-20261123/README.md`. [belief: cc]

## RTG-ASK-1 log replay (ak1123)

- Logs only: 126 progress JSONL files (digest c01b6b49...586c), 167,076 episodes, 127,966 escalation-eligible. Script `scripts/analysis/rtg_ask1_log_replay.py`, results `research/deep-dives/intake-ak-1123/rtg-ask-1-results.md`.
- Counts: 3,154 policy escalations, 0 logged model-initiated `escalate()`, 1,632 plan_reviewed consults. Entropy-only baseline unavailable (entropy never logged); ask-time probe holdout AUROC 0.593 (n=37,503). M4 did not fire (not evaluable). Budget-price replay invalid (selection-confounded uplift). Box ticked as counts-plus-stop; needs entropy and escalate/consult telemetry.

## Closeout (main session)

- TOC-SUPERSEDE-1 closed as SPLIT by operator decision (AgentDiet skipped; the subagent's refused extraction-script write, which it then wrote via a shell heredoc, was not re-attempted). M2 dormant.
- Filed TOC-SUPERSEDE-REPL-LOG (context-and-token-economy.md) and RTG-ASK-TELEMETRY (routing-program.md); both gated on post-reload traffic.
- KV-EVICT-COST-1 smoke, both telemetry boxes and the sampler-tap commit (orch e21a312e7049) join the STACK-UP-RELOAD-QUEUE.
- Taskflow r6c/r7d (pipeline-mgmt): 0/8 verified either arm; briefs move failures from "never edits" to "edits but fails". Lesson for WORKER-TASK-BRIEF: give the 35B relative paths, resolve in the harness. Orchestrator already parses reasoning_content (llama_server.py:1027/2144); measured-rate wall budgets to fold into the WORKER-TASK-BRIEF plan.
- Wrap-up: index --check rc=0; belief ledger fresh (lag 0); wiki delta 63 sources and research README (60 days) dispatched to subagents.
