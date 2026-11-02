# ws58 intake 2026-11-02: Jev harness engineering, the DeepSeek Super-agent essay, typed loop decisions and an agent-loop GUI

Session `intake-ws58-jev-20261102`. New entries **intake-2604 .. intake-2616**. The integrator was Opus,
and 8 sonnet subagents did the work:
- 3 primary-source dives (the Jev harness, the Super-agent essay, foreman with the LangChain blog);
- 2 loop-code surveys;
- 1 GUI survey;
- 1 literature expansion;
- 1 selective-prediction Stage-2b dive.

No compute was used.

Operator pre-approval (2026-11-02):
- Accept all recommended dives and literature expansions, up to two Stage-2b waves.
- Prepare the Stage-3 handoff changes, but do not apply them.

## Sources and dives

| Intake | Source | Verification | Dive file |
|---|---|---|---|
| intake-2604 | github.com/Archive228/jev-harness-engineering @ 5d8670b (MIT), plus the X post that links to it | dive-verified | [intake-2604-jev-harness-engineering.md](intake-2604-jev-harness-engineering.md) |
| intake-2605..2608 | arXiv 1705.08500, 2307.01928, 2107.11277, 2306.10193 | dive-verified (Jev Stage-2b wave 1) | [selective-prediction-wave1-dives.md](selective-prediction-wave1-dives.md) |
| intake-2609..2612 | apache/burr (dive-verified, 2 anchors); xyflow, mermaid, xstate (stage1-unverified) | GUI expansion | [agent-loop-gui-survey.md](agent-loop-gui-survey.md) |
| intake-2613..2614 | thruwire/foreman; LangChain "Building a Harness with Jev" | dive-verified (Jev Stage-2b wave 2) | [wave2-dives.md](wave2-dives.md) |
| intake-2615 | DeepSeek Harness Super-agent essay (the X Article linked from https://x.com/DeepSeekHarness/status/2116857257245987236) | dive-verified, read in full | [intake-2615-superagent-essay.md](intake-2615-superagent-essay.md) |
| intake-2616 | Anthropic "Scaling Managed Agents" (section "Decoupling the brain from the hands") | dive-verified (essay Stage-2b wave 1) | same file |

Notes were added, without creating a new entry, to three existing entries:
- **intake-1472** (docs.typesafe.ai). The docs now publish the Choice confidence formula, and jev-1.14 has replaced jev-1.13.
- **intake-146** (langgraph). LangGraph Studio is hosted, not in the repo.
- **intake-2603** (the dsh-superagent prototype). It now cross-links the essay, intake-2615.

### Reachability

- **Jev X post:** reachable. It links to an X article that is a shortened edition of the repo article, so it is recorded on intake-2604.
- **`typesafe.ai/docs`:** returns 404. I read `docs.typesafe.ai` from disk instead.
- **Super-agent essay:** reachable in the English machine translation.
- **Chinese original:** not found in bounded searches. This is recorded as unverified. It is not evidence that the original does not exist.

## Corrections to the operator summaries

**Jev (intake-2604)**
- The article does not say that question wording is versioned with its threshold. It says to pin the model version when tuning a threshold.
- "Low confidence = no opinion" and "asked / not asked / unavailable" are not stated principles. They are structural features: an unconfident or unavailable Choice stops with a reason.
- The 300 s limit appears only in the Codex policy. The default is 120 s.
- A fixed diagnostic order repaired 3 of 3 defects, against 2 of 3 for Jev. The author says no Jev advantage is established.
- "83 checks" is the harness's unit-test count, not the size of the diagnostic registry.
- jev-1.13.0 has been superseded.

**Super-agent (intake-2615)**
- All numbers are confirmed, but the essay calls them indicative. The ablation simulated the coding work, and the stress-test Workers were mocks.
- Removing pass-through left completion time unchanged. The +37% is Router cache-read tokens.
- Super-agent spends *more* cache-read tokens than a single session.
- Full-duplex start/stop exists but is not enabled by default.

Bottom line: the value of both sources is **control-flow discipline**, not a model. Every portable pattern works with any scorer that returns a probability vector.

## Stage 3: answers to the operator's questions

Code was read at:
- epyc-orchestrator `02a152a8`;
- epyc-root origin/main as of 2026-11-02;
- epyc-inference-research origin/main, under `scripts/kernel_rnd/autokernel/loop/`.

### Q1. Do these techniques help our loops?

**Autopilot: YES. The largest gain.**
- **T6 is a live latent defect.** `orchestration/repl_memory/q_judge.py:153-157` turns a judge timeout or exception into `SCORE: 1`, and `_parse_score` defaults to 1. An unavailable judge therefore reads as an answered low score. The judge is off by default (`q_scorer.py:1146`), so the defect is latent, but it fails open.
- **T1:** `_classify_meta_halt` (`scripts/autopilot/autopilot.py:8293`) is a count heuristic. It should emit a typed record in shadow mode.
- **T3:** planner actions are free text checked against a schema (`controller_io.py:768`, `:1027`). They should be a closed registry of diagnostic ids.
- **T4:** halting is a counter (`autopilot.py:10399`). It should be a named StopReason enum.
- **T5:** journal snapshot replay exists, but it needs a threshold-override divergence mode.

**AutoKernel: already largely conforms. Small tidy-up only.**
- Worker reports are re-extracted rather than trusted (`actors.py:1560`).
- The narrow decline question (`actors.py:1564-1640`) is the closest existing T1.
- `oracle_unavailable` is kept distinct (`loop.py:782-786`).
- Budgets exist (`resume.py:1004-1030`).
- Gap: `resume.ineligible_reason` (`:991`) returns free text, not an exhaustive enum.
- T3 adds little here, because AK gates are fixed code.

**Backlog churn: YES. The clearest typed-judgment target.**
- `handoff_sessions.work_state` (`:923`) decides by regex over Markdown.
- `rowflow/publish_row.py:82-104` classifies dry-run FAILs by regex and falls through to `UNKNOWN-FAILURE-CLASS`. Its repair table is already a registry, so the T3 shape exists.
- `MAX_FAILS=3` parks the row with no named stop enum.
- Nothing replays `dryrun/*/FAIL-*.json` under changed rules.
- `file_result.decide` (`:161`) already separates pass, fail and inconclusive. It lacks an explicit unverified list with provenance.

**Local typed-judgment model.**
- The learned router (`routing_classifier.py:126-142`) already returns a softmax with per-class abstain. `verifier_head.py` adds P(correct). Together they form a working two-threshold design, but only over routing actions.
- QScorer is a reward/Q-update agent, not a judge.
- For park / resume / done and failure classes, use one of two options:
  - a small local LLM that scores the options in one pass (in the jevlike style, intake-1462);
  - a small classifier trained on journal outcomes.
- Thresholds should come from risk-coverage or conformal calibration (intake-2605..2608), under three constraints:
  - Labels must be real outcomes, never the judge's own output.
  - Use one decision per episode, because steps within an episode are not exchangeable (operator-review candidate from the intake-2608 dive).
  - Hold out a test split for replay.

### Q1b. The Super-agent essay mapped to the churn pipeline

| Element | Ours | Lack or worse |
|---|---|---|
| Router / Workers | `handoff_sessions.py` is a zero-token Router (`:3`) that starts and resumes per-handoff Workers (`:22-29`). codex-gen is a long-lived generalist for small tasks, not a router. | The Router has no admission judgment: it admits on static rank alone. |
| Fast / Slow filter | Fast path: `wrapped()` gate (`:1197`), `MIN_RESUME_GAP_S` (`:838`), `await_event` no-op skip (`:1227`). | No slow path: nothing decides whether an event or slot is worth a turn before a fresh start. |
| Threads + subscriptions | `awaiting/*.json` and run-end `pending_event`, routed by slug in code (`:578`, `:1034`, `:1202`). This is already pass-through without a Router call. | Each delivery resumes a process and re-reads cold context, rather than reaching a standing live Worker. |
| Router batching | Events queue while the pid is alive and the next resume carries all of them (`:1193-1197`). | Per slug only. Adequate. |
| Full-duplex start/stop | The run-end `.ended`/`.complete` files are the async result. "No in-turn waiting" is our version, and it is sound: the essay's own full-duplex mode is not enabled by default. | No mid-turn re-signal. Low priority. |
| Inline/Spill, Chain of Recall | Briefs (cold start) plus `delta(slug)` on resume (`:1219`). | Events do not carry related ids, so a resumed Worker re-derives context. |
| Watchdog | Keeper watchdog (infrastructure liveness only). | Nothing watches for unproductive loops: many fresh starts with no effect. |

**What the essay argues against: the slot-thrash of 2026-11-01/02.**
- In `/mnt/raid0/llm/tmp/compute-flags/handoff-sessions.log`, 61 of 63 `AUTO-START` lines carry `rows=-`. 44 of them fell in about 43 minutes, between 23:31Z and 00:14Z.
- Cause:
  1. `candidates()` (`handoff_sessions.py:735-745`) requires only `open_tasks > 0`.
  2. `backlog_gen` scores an unpublished inference task at 0.5, so a handoff with zero ready rows still ranks.
  3. `auto_start()` (`:791-831`) refills every freed slot with a `fresh=True` bootstrap.
  4. It re-admits a handoff that has just finished (`restarted_from_done`), with no cooldown.
- The essay's own words go against this. Giving every event its own new session "reverses the trade-off": it loses shared context. The design is one long-lived Worker per task, subscribed to its thread (intake-2615).
- Anthropic measured the cost of per-session bootstrap and the TTFT gain from removing it (intake-2616, vendor measurement).
- Smallest fix: admit only handoffs with a ready row (or pinned ones), add a per-slug start cooldown and a global hourly start cap, log `AUTO-START-THROTTLED`, and alarm from a zero-token watchdog counter (SA-1, SA-2).

### Q2. A GUI for designing and debugging loop flows

Recommendation: **spec-first, viewer-first, on the existing hub.**

1. **Typed loop spec.** JSON plus JSON Schema, holding `states`, `transitions{from,to,guard,threshold_ref}`, `stop_reasons` and `thresholds{name:{value,unit,direction}}`. Each loop owns its spec next to its code. Write the churn spec first: its states are visible in `handoff_sessions.py`.
2. **Phase A, viewer.** A registered hub page renders the spec as a Mermaid state diagram (vendored and pinned), or as inline SVG in the style of the cockpit provenance graph. It needs a registry entry, a health probe and a freshness envelope, per `dashboard/README.md`.
3. **Phase B, replay stepper.** A pure `step(spec, saved_input, n)` returns `(state, fired_transition, stop_reason)`. The page scrubs through saved journal or FAIL inputs and highlights the fired edge. A threshold slider shows the first diverging step, which is the Jev replay idea. The data model is per-step snapshot plus parent pointer, as in Burr (intake-2609).
4. **Phase C, round-trip edits.** Threshold and field edits only. The page emits a JSON patch, and the owning session validates and applies it. The existing JSON Canvas import/diff (`epyc-orchestrator src/canvas_import.py:116-438`) is the alternative that needs no new UI. Structure editing with xyflow waits until Phases A and B have users.

Rejected as embedded runtimes:
- LangGraph Studio, because it is hosted.
- Stately inspect, because its UI is hosted by default.
- Node-RED, Langflow and Flowise, because each brings its own application plane.

## Proposed task lines (prepared, NOT applied: they need operator plan approval)

| ID | Owner (proposed) | Task |
|---|---|---|
| SA-1 | session-bus-thin-dispatcher.md (churn) | `- [ ] SA-1: auto_start admits only handoffs with a ready row (or pinned); per-slug AUTO_START_COOLDOWN_S + global starts/hour cap; log AUTO-START-THROTTLED; test rows=[] and just-done fixtures` |
| SA-2 | session-bus-thin-dispatcher.md | `- [ ] SA-2: zero-token watchdog counts AUTO-START/DONE per hour vs ready rows unclaimed; alarm on starts>cap with no effect` |
| SA-3 | session-bus-thin-dispatcher.md | `- [ ] SA-3: run-end/awaited events carry related ids (row, run, handoff) so a resumed worker gets a chain-of-recall delta, not a cold re-read` |
| SA-4 | agent-loop-design.md | `- [ ] SA-4: guide rule — long-lived worker per task with code pass-through; fresh start only on a ready row; watch for unproductive loops` |
| JEV-1 | epyc-orchestrator autopilot handoff | `- [ ] JEV-1: q_judge returns (None,"unavailable") on timeout/exception/unparseable; callers count unavailable separately; regression test` |
| JEV-2 | autopilot handoff | `- [ ] JEV-2: _classify_meta_halt emits {label,probs,confidence,judge_state} journal record in shadow; StopReason enum; replay prints rows a threshold change flips` |
| JEV-3 | session-bus-thin-dispatcher.md | `- [ ] JEV-3: shadow typed judgment beside work_state and publish_row FAIL classification; replay over dryrun/*/FAIL-*.json prints label diffs; named park/stop enum` |
| JEV-4 | AK harness handoff | `- [ ] JEV-4: resume.ineligible_reason returns an exhaustive code enum + text; audit critic/panel calls record asked/answered/unavailable` |
| JEV-5 | agent-loop-design.md + hub dashboard owner | `- [ ] JEV-5: loop-spec JSON schema + Phase A Mermaid viewer page (registry+probe+freshness) for the churn loop; then Phase B replay stepper` |
| JEV-6 | agent-loop-design.md | `- [ ] JEV-6: guide rule — typed judgments carry probs+confidence, two thresholds set by risk-coverage on held-out real outcomes, unavailable != answered, worker claim never a result` |

Minimum-rigor notes:
- JEV-2 and JEV-3 run in shadow only. Their deciding evidence is a replay over saved inputs, with a held-out split and real outcome labels. Activation needs a separate gate.
- SA-1 is deterministic infrastructure. Its conformance check is a unit-test fixture plus the count of `AUTO-START rows=-` lines in the next 24 h of the log, which should be zero.

## Stage 4 filing (operator approved 2026-11-02: "Approve, go to Stage 4"; D9 acknowledged for scripts/coordination)

Filed as written in the owning handoffs, with these changes from the draft above:
- SA-1..4, JEV-3 and JEV-6 went to `handoffs/active/churn-pipeline.md` (RTG-62), not to session-bus-thin-dispatcher.md.
- SA-1 is merged into the in-progress sticky-slot change.
- JEV-3 and JEV-2 **replace** the regex/heuristic classifiers with the local native `src/typed_decisions/` path (TD-29). Replay of the saved FAIL inputs is a regression check only, and there is no new accuracy study.
- Every task line carries a "removes:" clause (deletion-first).

Owners:

| Handoff | Tasks |
|---|---|
| autopilot-continuous-optimization.md | JEV-1, JEV-2 |
| autokernel-research-loop.md | JEV-4 |
| dashboard-architecture-restructure.md | JEV-5, KT-3 |
| internal-kb-rag.md | KT-1, KT-4 |
| vidya-belief-substrate-program.md | KT-2 |
| dev-harness-trace-mining.md | KT-5 |

**Order:**
1. SA-1 + JEV-1.
2. SA-2, SA-3, JEV-3.
3. JEV-5 phase A, KT-1, KT-3.
4. The rest. JEV-5 phases B and C come only after the operator has used phase A.
