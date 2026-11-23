# RTG-ASK-1 results (logs only, 2026-11-23)

Script: `scripts/analysis/rtg_ask1_log_replay.py <progress_dir> <out.json>` (stdlib, ~100 CPU-s, reproducible).
Frozen manifest: `epyc-orchestrator/logs/progress/*.jsonl`, 126 files, 2026-02-27 .. 2026-11-19, 1.7 GB, digest-of-sha256s `c01b6b496dfd09e7c1bf8ce11da7ca7aa7ff3f9afcfc3c94ace9a8ae0321586c`.
Inference taps (`/mnt/raid0/llm/tmp/inference_tap_events.jsonl`, `repl_tap.log`) were also checked: no entropy/logprob field and no `escalate()` text.

## Question and noise floor
Q: can a logged-feature residual-risk probe beat the entropy-only baseline by >= 0.05 holdout AUROC, and what do `escalate()` vs consult counts and a budget-priced penalty look like? n = 167,076 episodes; 127,966 escalation-eligible (first route not architect-tier); gate of 200 passed. Holdout AUROC noise floor: bootstrap 95% half-width about 0.012 (n=37,503).

## (a) Counts
- `escalation_triggered`: 3,154 events over 2,749 episodes. Reasons: 1,643 "repeated nudges", 1,511 "failures". These are rule-policy escalations (escalation.py).
- Model-initiated `escalate()` hand-offs (graph/nodes.py writes the prefix `Model-initiated:`): **0** in all logs. So the REPL `escalate()` hand-off is not distinguishable/observed; the tool-call count is zero or unlogged.
- Consults: not tapped as an event. Only consult-like record is `plan_reviewed` (architect plan review): 1,632.
- Per first-routed role (policy escalations / plan_reviewed / episodes): frontdoor 2971/921/77,259; worker_general 113/338/29,516; coder_escalation 23/71/13,078; worker_vision 24/140/6,721; ingest_long_context 3/151/10,172; toolrunner 12/0/24; architect_critic 8/0/64; architect_general, architect_coding, worker_math: 0.

## (b) Probe vs entropy-only
- Entropy-only baseline: **UNAVAILABLE**. `generation_monitor` entropy is not logged anywhere (0 episodes with entropy). No entropy-only AUROC can be computed without inference.
- Probe pool: 125,008 non-escalated, non-infra eligible episodes (282 infra and 2,676 escalated excluded). Label = episode outcome != success. Time split 70/30: train 87,505 (2026-02-27..07-06, fail rate 7.9%), holdout 37,503 (07-06..10-01, fail rate 5.3%).
- Ask-time probe (factual_risk, difficulty, prompt length, role one-hot), logistic: holdout AUROC **0.593** (bootstrap 95% 0.581-0.604).
- References: difficulty_score alone 0.482; factual_risk alone 0.535.
- Probe with post-generation features (tokens, answer chars, ms/token): 0.876, **leaky** (failed answers are short/empty; not available at ask time). Not a valid result.
- **M4 did not fire** (not evaluable): there is no entropy-only number, so the >= 0.05 margin cannot be established. The ask-time probe is itself near chance (0.59). Not adopted.

## (c) Budget-priced penalty replay
Observational uplift per (role x risk band) cell = P(success | escalated) - P(success | not). 9 usable cells (>=5 per arm). Escalated episodes are selected by failure, so uplift is negative or near zero in every cell (best +0.056 worker_general|low; frontdoor cells -0.54..-0.96). Fixed 0.15 rule: 0 cells escalate. Budget-priced (cap at 1.0x / 0.5x / 0.25x of observed escalation volume): priced lambda -0.96 / -0.54 / -0.54, i.e. a negative price; 9 / 6 / 6 cells "escalate" and all differ from the fixed rule, an artifact of the selection confound. Conclusion: the logs cannot price consults; a counterfactual (randomised or paired) arm is required. Per-episode output file not emitted (aggregates only; rerun the script for cell tables).

## Stop
Entropy and `escalate()`-call telemetry are missing. Needed: log `generation_monitor` avg/current entropy and the `escalate()` tool call + consult events per episode. Until then (b) and (c) cannot be answered from logs.
