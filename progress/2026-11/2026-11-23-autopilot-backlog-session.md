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

## Post-reboot Autopilot sequence and hold audit (ap-postreboot-audit)

- Recorded the operator-agreed sequence (reboot, ALFWorld smoke, Life-Harness run with R1-R5 accept, fold-in decision, journal-staleness audit LAST, operator lifts hold) as "2026-11-23 post-reboot sequence" in `handoffs/active/autopilot-program.md`, with the full audit table of every box waiting on the hold or relaunch (BEFORE / WITH / AFTER).
- Filed AP-POSTREBOOT-LH-RIGOR, AP-POSTREBOOT-ALF-SMOKE, AP-POSTREBOOT-LH-RUN, AP-POSTREBOOT-FOLDIN-DECISION and AP-BSV2-RIGOR-GATE-CODE; AP-JOURNAL-STALENESS-AUDIT now gated on AP-POSTREBOOT-FOLDIN-DECISION.
- Fixed stale text in place: BSV-2 "R1-R5 waits on the audit" (code does not need the loop), M10 trigger in `eval-tower-program.md`; pointers added at HIL-6, STACK-UP-RELOAD-QUEUE and stage-3 AKI-45.
- Open ordering question recorded (not decided): W-11/W-13 still require the v11 promotion and PIP02-PADDLE-STACK-ENTRY before the lift; the agreed sequence is silent on both.
- No inference, no process started. [no-belief: documentation and audit]

## AP-BSV2-RIGOR-GATE-CODE (non-inference, code + unit tests)

- Orchestrator commit `31ee413c` on main (rebased from `3f14c783`): R1-R5 in `scripts/autopilot/bsv2_accept_rigor.py`, called from `actions._bsv2_accepts` (prompt, GEPA, code paths) behind new default-off sub-flag `AUTOPILOT_BSV2_ACCEPT_RIGOR` under the existing `AUTOPILOT_BSV2_ACCEPT_GATE`.
- Wired: FeatureSpecs `autopilot_bsv2_accept_gate` and `autopilot_bsv2_accept_rigor`, `runtime_flags.spec.yaml`, `HOT_SWAP_FEATURES`, `scripts/autopilot/program.md`.
- Tests (fakes only): 12 new pass; test_runtime_flag_spec, test_features, test_flag_surface, test_ap72_speed_ceiling_table 165 pass; existing `-k bsv2` actions tests 3 pass. System pytest with the orchestrator venv python (venv has no pytest).
- Fails closed on unknown proposal-qid set; live use needs the loop to populate `state["bsv2_rigor"]`. Open: the gate flags are proposer-flippable (hot swap); pinning needs a `test_flag_surface.py` change. Autopilot not started. [no-belief: build/landing]

## AP-BSV2-RIGOR-PIN and AP-BSV2-RIGOR-STATE (non-inference, code + unit tests)

- Orchestrator commit `3421892f` on branch `ap-bsv2-rigor-pin-state` (worktree `/mnt/raid0/llm/worktrees/bsv2-rigor-pin`), PRE-PUSH and may be rebased.
- PIN: both BSV-2 flags moved from `HOT_SWAP_FEATURES` into `PINNED_OBSERVE_ONLY_FLAGS` (the proposer's propose/apply paths refuse them); FeatureSpec, `runtime_flags.spec.yaml` and operator settability kept; `program.md` says observe-only; `test_flag_surface.py` pinned-set assertions updated.
- STATE: `dispatch_action` populates `state["bsv2_rigor"]` (proposal batch = previous eval qids, sealed hash split, budget unit/limit) when gate+rigor are on, and `EvalTower.bsv2_exclude_qids` partitions the T1 accept draw away from proposal and sealed qids. Unit tests: valid accept passes, overlapping and sealed accepts refused, unknown batch fails closed, inert when off.
- Tests: 153 pass (rigor, flag_surface, repl_child_lane_full); 234 pass on actions/config_applicator/eval_tower hybrid+partitions/structural_lab neighbours. Autopilot not started; nothing pushed. [no-belief: build/landing]

## AP-POSTREBOOT-LH-RIGOR built (ap-lh-rigor-20261123)

- Built the R1-R5 accept enforcement, loopback proxies, improver-conformance replay and launcher for the Life-Harness ALFWorld run in `scripts/harness/life_harness/` with `tests/harness/test_life_harness_glue.py` (39 pass, fakes only); box ticked `[no-belief: build/landing]`.
- Design: the shipped round accepts on the same 50 tasks that fed the proposer, so each round now evaluates the incumbent on P_n, then a fresh parent and the candidate on a disjoint accept batch A_n; 1010 solver episodes (shipped 710).
- Stood up the native ALFWorld env without Docker (venv, extracted data, `smoke_alfworld.py` passed); AgentRL controller binary downloaded and SHA-verified but not executed (controller/worker step classifier-denied, not retried).
- Found and worked around eight upstream defects without editing the clone; the list and the launch recipe are under the box in `handoffs/active/autopilot-program.md`.
- No inference, no model server; network use was package, tokenizer and controller-release downloads only. [no-belief: build/landing]

## Research intake: nanocode resubmission (re-encounter)

- Operator resubmitted https://github.com/nanocodexyz/nanocode/; the unbounded dedup found an exact url collision with intake-2789 (ingested, dived and plan-approved 2026-11-22).
- Per intake rule 2b no new entry or dive was made; a re-encounter line was added to intake-2789 notes only. No Stage-3 plan was produced because the existing one (research/deep-dives/pm-intake-nanocode-20261122/stage3-plan.md) is already approved and filed. [no-belief: duplicate re-encounter]

## Operator decision: distill Life-Harness into the Autopilot (AP-LH-DISTILL built)

- Decision (operator, 2026-11-23): the Life-Harness harness-optimization ideas go INTO the Autopilot proposers; the full ALFWorld Life-Harness run is parked, optional. AP-POSTREBOOT-FOLDIN-DECISION ticked (`[no-belief: operator decision]`); AP-POSTREBOOT-LH-RUN re-scoped parked/optional by sub-bullet; AP-POSTREBOOT-ALF-SMOKE unchanged (5 episodes, plumbing); AP-JOURNAL-STALENESS-AUDIT gate changed from AP-POSTREBOOT-FOLDIN-DECISION to AP-LH-DISTILL via `handoff_box.py gate`, so nothing on the relaunch path waits on LH-RUN. Sequence text: step 2 is now "build the distilled proposer (no compute)", step 3 is done.
- New boxes: AP-LH-DISTILL (ticked, `[no-belief: build/landing]`) and AP-ALFWORLD-SUITE (ALFWorld as a small rotating EvalTower slice via the native env and proxy in `scripts/harness/life_harness/`; adapter build now, one 5-episode live slice after the smoke; gate AP-POSTREBOOT-ALF-SMOKE).
- Orchestrator commit `d88070d9f` on branch `ap-lh-distill` (worktree `/mnt/raid0/llm/worktrees/ap-lh-distill`), PRE-PUSH and may be rebased. New `scripts/autopilot/harness_layers.py`: four layers (action_realization, environment_contract, trajectory_regulation, procedural_skill) plus legacy kinds prompt/routing/flag, annotation only; each layer maps onto EXISTING flags, prompt files, allowlisted code files and the `distill_skillbank` action (a test asserts every mapped name resolves). The mutation proposer's failure context carries the implicated layer and the surfaces per layer; the layer is journaled in `eval_details.details.harness_layer` (skipped rows via `SkipOutcome.lh_annotations`); an optional `layer` action key is outside config identity.
- Trace-replay pre-check: a `structural_experiment` enabling one guard flag is replayed with no model call against the newest failing traces of the contrastive bank; six guard flags have over-approximating firing predicates; a proved no-op is skipped before apply or eval (`skipped`, reason `trace_replay_precheck`, not blacklisted); truncated traces are inconclusive; prompt and code edits record `not_replayable` and proceed.
- Flags, both default off and hot-swappable: `autopilot_lh_layer_taxonomy`, `autopilot_lh_trace_replay_precheck` (FeatureSpec, Features field, `runtime_flags.spec.yaml`, `HOT_SWAP_FEATURES`, `program.md` Tier 2b rows, chapter 01 table). Tests: `tests/unit/test_harness_layers.py` 51 pass (fakes only); touched neighbour suites (actions, controller_io, bsv2_accept_rigor, features, runtime_flag_spec, config_applicator, config_fingerprint, core_contracts, tool_surface, gate_frontier) 433 pass. Autopilot not started; nothing pushed. [no-belief: build/landing]

## AP-LH-DISTILL audit fixes (independent audit of `d88070d9f`)

- Orchestrator fix commit `09538ffbc7124d5eaba9746a13742521303013cb` on top of `d88070d9f` (branch `ap-lh-distill`, same worktree; new commit, no history rewrite), PRE-PUSH. Autopilot not started; nothing pushed.
- Pre-check soundness: the trace bank is fed from the last 50 lines of the inference tap (LLM text only; REPL results live in `repl_tap.log`), so a trace with no truncation marker is still not a whole trajectory. Bank items now carry `complete` (default False) and `source` (default `inference_tap_tail`); a rejecting `would_not_fire` needs every motivating trace to be `complete=True` with no `[trace truncated]` / tap `... [N chars truncated]` marker, else `inconclusive` and the eval runs. Net effect today: the pre-check never rejects (observe-only). Whole-trajectory capture filed as box AP-LH-WHOLE-TRAJECTORY-CAPTURE.
- Predicates now import the real guards' patterns (`tool_arg_guard.LEAK_MARKERS`, `answer_resolution._PLAN_LINE_RE`); failure-ratio is case-insensitive and counts `[ERROR` / `[TOOL ERROR`; `stream_degeneration_guard` and `tool_call_parse_error_retry` dropped (not decidable from text, `not_replayable`). Negative-direction tests drive the real guards (`find_leak`, `_looks_like_plan_narration`, `_note_turn_health` + `_harness_failure_ratio_tripped`, `_guard_syntax_loop`) and require the predicate to fire wherever they do.
- Skip rows journal under `eval_details.details` (same path as executed rows); the `layer` action key is accepted only while `autopilot_lh_layer_taxonomy` is on (flags-off identical to before, validation and JSON schema); docs say replay skips count toward the consecutive-skip pause and reach the planner, and no longer call a rejection a proof.
- Tests: `tests/unit/test_harness_layers.py` 85 pass; with test_autopilot_actions, test_autopilot_controller_io, test_features, test_runtime_flag_spec, test_config_applicator, test_eval_tower_hybrid_eval, test_autopilot_sequential_wiring 486 pass; test_stack_change_guard + test_m27d1_source_label_flag 158 pass.
- Root handoff: AP-JOURNAL-STALENESS-AUDIT gate back to none (sub-bullet: must cover `harness_layer` / `trace_replay_precheck`); AP-ALFWORLD-SUITE gate removed (adapter needs no compute; live slice still follows AP-POSTREBOOT-ALF-SMOKE); AP-POSTREBOOT-FOLDIN-DECISION refined to AP-POSTREBOOT-FOLDIN-DECISION-DISTILL (done-when matches the decision taken; ticked `[no-belief: operator decision]`). [no-belief: build/landing]

## Closeout 2 (main session, operator /wrap-up)

- Fable audit of the distill (`d88070d9f`): wiring, flag inertness, no new surfaces, pinned accept-gate flags and determinism clean; two must-fix soundness findings (the trace bank is a tap tail, not a trajectory; four predicates under-approximated their guards) fixed in orch `09538ffbc`; re-verified by the same auditor ("PUSH both"). Both repos pushed; reviewer nits applied (REPL failure tagging in AP-LH-WHOLE-TRAJECTORY-CAPTURE done-when; step 3 names the -DISTILL box).
- Operator decisions today: post-reboot sequence (smoke → distilled proposer → journal audit → hold lift after v11 + PIP02); W-11/W-13 kept; Life-Harness distilled into autopilot, full ALFWorld run parked optional; TOC-SUPERSEDE-1 closed as split.
- nanocode resubmission: duplicate of intake-2789 (approved 2026-11-22); re-encounter note only.
- In flight at wrap-up: AP-LH-WHOLE-TRAJECTORY-CAPTURE and AP-ALFWORLD-SUITE adapter builds (subagents).
- Wrap-up checks: index --check rc=0; belief ledger fresh (lag 0); no prune candidates; wiki delta 18 sources (the large handoffs deliberately left uncompiled at the earlier sweep; not swept now). Research README still 60 days stale: its refresh is blocked by Edit hook 20 on a pre-existing broken `../../MEASUREMENT.md` link, which the operator chose to fix by hand (not yet on origin/main); the verified edits are ready to apply after.

## AP-LH-WHOLE-TRAJECTORY-CAPTURE built (ap-lh-wtc)

- Orchestrator commit `4c07ffd5af6f307b41c6519c61ad93eeb2cd265b` on branch `ap-lh-wtc` (worktree `/mnt/raid0/llm/worktrees/ap-lh-wtc`, on top of `09538ffb`), PRE-PUSH, may be rebased. No inference, no server, autopilot not started, nothing pushed.
- Join key found, not guessed: eval tap events carry no `trial_id` (the tower never sends one), so a trial is joined through the tower's own `eval_batch_id` (the `batch_id` on every dispatched request and on every event of `inference_tap_events.jsonl`; recorded per trial by `EvalTower.note_trial_batches`), then `task_id` into `repl_tap.log`. The plaintext tap is unusable (chunks carry no ids, interleave under concurrency) and the legacy REPL result block has no task id, so with the new flag on each result block gets a `[turn N] RESULT | task_id=X | chars=L` header (flag off: identical bytes).
- New `scripts/autopilot/whole_trajectory_capture.py` (flag `autopilot_lh_whole_trajectory_capture`, default off, fully wired: FeatureSpec, `runtime_flags.spec.yaml`, `HOT_SWAP_FEATURES`, program.md and chapter 01 rows): binary-searches both files to the trial window, joins LLM turns and REPL results with no tail cut, tags each failing REPL turn with the fixed `[REPL TURN ERROR]` line, and banks the failure item `source=whole_trajectory`, `complete=True` only when completeness is proven; any gap or a cap hit (256 KiB per trial, head kept, `[trace truncated]` prefix) banks `complete=False` with named reasons. Bank items gain `full_trace` (newest 2 failure items only, state-size bound).
- Tests: `tests/unit/test_whole_trajectory_capture.py` 23 pass (would_not_fire on a complete item, inconclusive on a tap-tail item, failure tags matched by the failure-ratio predicate, cap hit incomplete, flag off unchanged, concurrency attribution, binary-search window); with test_harness_layers, test_autopilot_actions, test_features, test_runtime_flag_spec, test_config_applicator, test_autopilot_sequential_wiring, test_eval_tower_hybrid_eval, test_repl_tap_meta, test_graph_helpers, test_repl_harness_guards 502 pass (async tests skipped by the venv, none failed).
- Not measured (needs a running stack): the real `complete=True` share per trial (cap-hit and tap-cut rates decide whether 256 KiB is the right cap).
- Box AP-LH-WHOLE-TRAJECTORY-CAPTURE ticked in `handoffs/active/autopilot-program.md`. [no-belief: build/landing]
