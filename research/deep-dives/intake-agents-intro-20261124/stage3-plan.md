# Stage-3 plan — intake-agents-intro-20261124 ("The Little Book of Agent Engineering")

**Status**: PROPOSED. Awaiting operator approval. Nothing here has been applied to any handoff or index.
**Lane**: `/mnt/raid0/llm/worktrees/intake-agents-intro-20261124` (branch `intake/agents-intro-20261124`,
base origin/main `b61af8f2a4b5`); orchestrator read at `1cc2043aa2d2`, research at `3ab8362e5b58`.
**Entries**: intake-2907..2941, 35 in all. The book stays stage1-unverified. The other 34 are
dive-verified. Dives are in `sweep1-reference-dives.md`, `sweep2-wave1-dives.md` and
`sweep3-wave2-dives.md`, in this folder.
**Subagents**: 14 sonnet (12 dives, 1 grounding scan, 1 clerk) and 1 haiku second reader. The integrator is
Opus 5.5.
**Renumbering**: other intakes landed intake-2864..2906 on origin/main (`d00f06572941`) while this
lane ran. This session's 35 entries were renumbered +43, to intake-2907..2941, in this prepared
package. The intake id is the identity; the lane's original numbers 2864..2898 are dead and appear
nowhere in the package. The ledger row ids (`iNNNN-A1`, ...) are opaque labels and were renumbered
the same way.
**Apply package**: `/mnt/raid0/llm/tmp/dive-agents-intro/prepared/`. It holds
`intake_index.patch`, a pure append of 3,467 lines against origin/main `d00f06572941`, with anchor
marks already script-written. It also holds `.research-session.json`, the three sweep files, this
plan and the README.
**Plan file path on apply**: `research/deep-dives/intake-agents-intro-20261124/stage3-plan.md`.

## Headline

The book is a sound synthesis. Ten of its references were dived. Three of its characterisations held as
stated, six were narrowed, and one was not found in its source: the p.160 claim that accuracy rank and
reliability rank are unrelated appears in neither HAL nor the reliability paper. One citation is wrong
(the CooperBench title). Two waves of follow-up sources turned up five concrete gaps in EPYC code or
process. Each gets one packet below. Everything else is already covered by existing boxes, or waits on
a named trigger.

## Work packets

| Packet | Action | Owner | Posture |
|---|---|---|---|
| P1 | Termination and observation hygiene: finish_reason on /chat; truncation markers that say how to narrow | handoffs/active/harness-program.md (track agentic-serving-harness-fixes) | primitive-now (deterministic) |
| P2 | Eval instrument integrity: drops manifest and graded-fraction imbalance flag; token span ratio; rerun-arm decision | handoffs/active/eval-tower-program.md (track scoring-infra-standardization) | primitive-now + operator decision |
| P3 | Reviewer arm protocol: fix/break and fairness report; A1 precheck; one bounded located/comprehensive probe | handoffs/active/reviewer-control-plane.md (track reviewer-model-ablations) | primitive-now + cheap-screen-now |
| P4 | Injection: CT-18 arm D tool-output sanitizer (prep, run); boundary-laundering lint; http_post guard | handoffs/active/harness-program.md (track harness-improvement-loop) | primitive-now + cheap-screen-now |
| P5 | kb-search breadcrumb-encoding side-index A/B | handoffs/active/knowledge-pipelines.md (track colbert-reranker-web-research) | cheap-screen-now |

**Dependencies and concurrency.** All five packets are independent and can run in parallel. Inside
packets: AEI-REV-A1-LOCATE-PROBE is gated on AEI-REV-A1-PRECHECK, and AEI-CT18-ARMD-RUN is gated on
AEI-CT18-ARMD-PREP. The zero-inference boxes in P1, P2, P3 and P4 need no compute window. The
inference boxes (P3 probe, P4 run, P5) are booked through the normal row flow.

### P1 — Termination and observation hygiene

- **Project decision**: should /chat clients and agents trust an answer as complete? Today a length-cut answer is indistinguishable from a complete one.
- **Pinned implementation gap**: the backend already maps finish_reason to completion_reason (`src/backends/llama_server.py:596-612, 1102-1111 @ 1cc2043`). The /chat response model has no finish_reason or truncated field (`src/api/models/responses.py`). The REPL handles `length` only behind default-off `reasoning_runaway_retry` (`src/graph/helpers.py:1951-2027`). Three markers append `[... truncated at N chars]` with no hint (`src/llm_primitives/primitives.py:1267, 1409, 1529`), while the REPL spill footer already says how to narrow (`src/repl_environment/environment.py:1008-1085`). UFH14-LB2 persists finish_reason in parse events, but that is telemetry only, not the response surface.
- **Operational opportunity**: return finish_reason and truncated on /chat; make the markers instructive.
- **Expected benefit direction**: fewer silent partial answers and fewer repeated full-output calls. Complete answers are unchanged.
- **Implementation / isolated-probe / activation**: code plus unit tests; no probe needed; activation is an API-only reload by the owning session.
- **Sources**: S1-1, S1-3, i2911-A2. intake-2911 claim 1 (25,000-token default cap, with truncation that steers the agent). The book's own wording is discovery only.
- **Enabling primitive**: none new; reuse completion_reason.
- **Consumers**: direct = /chat clients and the opencode shell; evidence = parse_events.
- **Rigor**: deterministic infrastructure. The controls are conformance tests (stop, length, context_limit fixtures) plus a negative test showing that a complete answer carries `truncated=false`.
- **Broader trigger**: none.

### P2 — Eval instrument integrity

- **Project decision**: can an AutoPilot keep/revert or a tower comparison be reordered by instrument artefacts instead of model behaviour?
- **Pinned gap**: EV-18 adds `quality_itt` and `itt_denominator` beside per-protocol quality (epyc-orchestrator `ea8c7338`, `3d8830ee`). Nothing flags two arms with different graded fractions, and no aggregate carries a drops manifest. No check proves that token accounting counts each call once. `measurement/protocols/quality-eval.md` P-AB-1/P-PAIRED have paired designs but no same-configuration rerun control.
- **Evidence**:
  - intake-2921 claims 0-2: in HAL, the Generalist was graded on 51% of episodes against 98% for Tool-Calling, and cost was doubled in 44 of 94 matched rows.
  - intake-2935: 0 of 50 audited repositories report failed runs beside the headline, and changing only the reporting rule moves scores by up to 20.9 points.
  - intake-2934: reruns flip as many tasks as a harness swap (about 13% median).
- **Opportunity**: AEI-DROPS-MANIFEST and AEI-TOKEN-SPAN-RATIO, both zero inference. AEI-RERUN-ARM-OD is an operator decision, because the measurement trust boundary is human-amendment-only.
- **Benefit direction**: fewer false keeps and reverts. Scorer semantics are unchanged.
- **Rigor**: deterministic, with fixtures for an equal and an unequal graded fraction. The span-ratio check has a predeclared rule: any ratio other than 1.0 is a defect and must be fixed.
- **Decision package for AEI-RERUN-ARM-OD**:
  - (a) Recommended: add a same-configuration rerun arm and report the rerun flip rate beside every scaffold, harness or reviewer-arm effect. The cost is one extra run per compared cell.
  - (b) Require it only for comparisons that drive a ratified claim. This is cheaper but leaves screening exposed.
  - (c) No change. The tower keeps paired single runs with the MDE rule.
  - Option (a) blocks only its own item.
- **Consumers**: direct = eval_tower aggregation and the AutoPilot quality-delta report; policy = keep/revert.
- **Broader trigger**: Pass^k and resource consistency stay under M2.

### P3 — Reviewer arm protocol

- **Project decision**: keep spending reviewer arm budget on A1 (self-review), or close it as a negative control?
- **Pinned gap**: RM-2 A1 live result is FA 45.8%, FR 41.7%, AUC 0.463 on 48 rows (reviewer-control-plane.md @ b61af8f). The calibration report (`scripts/analysis/reviewer_calibration_report.py:304-345 @ 1cc2043`) has consistency and pass_hat_k but no fix/break counts and no record of comparison fairness.
- **Evidence**:
  - Prompted intrinsic self-correction hurts (intake-2914 claims 0-1; intake-2930 claim 1 base 52.6 to 41.4).
  - The fair-evaluation checklist (intake-2929 claim 4).
  - Error location is the bottleneck (intake-2940).
  - A comprehensive single prompt beats multi-agent review at similar cost (intake-2937).
- **Opportunity**: AEI-REV-FLIPS (offline); AEI-REV-A1-PRECHECK (zero inference); AEI-REV-A1-LOCATE-PROBE (inference: arm L with oracle location, arm P with a comprehensive prompt).
- **Benefit direction**: reviewer budget moves off a near-chance arm, or A1 gains a mechanism-level reason to stay.
- **Six controls (probe)**:
  1. Frozen input: the same 48-row C-CRAB slice that RM-2 used, with digest recorded.
  2. Baseline: incumbent A1 (Qwen3.5-122B architect alias, CPU host).
  3. Per-item raw outputs: decisions.jsonl per arm.
  4. Holdout: not applicable to a diagnostic. Replacement check: the arms are a fixed protocol over identical rows, and no arm is tuned on them.
  5. Complete denominator: unparseable verdicts count as errors.
  6. Predeclared rule: see the stop rule below.
- **Stop rule**:
  - Question: does giving the defect location (L) or a comprehensive prompt (P) lift A1 discrimination?
  - Effect vs error: with n=48, only an AUC rise of about 0.15 or more, or an FA+FR fall of 20 or more points, can be told apart from noise.
  - Checkpoint at 24 rows. Stop for futility if arm L is not better than A1 on FA+FR at 24 rows.
  - Answer: if L lifts and P does not, the bottleneck is localisation, and the result routes to a detector design under M7. If neither lifts, close A1 as a negative control.
  - Evidence reused: the A1 48-row run.
- **Inference fields (hand-added at Stage 4)**: `· model Qwen3.5-122B (incumbent A1) · build production-consolidated-v10 · harness reviewer RM-2 runner · metric FA/FR (lower better), AUC (higher better) · rule above · region CPU host quarter · est ~2,200 s per arm from the A1 48-row run (2164 s)`.

### P4 — Injection defense measurement and two guards

- **Project decision**: do we have a measured defense layer beyond prompt wording for injected tool output, and are external sends guarded?
- **Pinned gap**:
  - CT-18 arms A-C exist with IB2 fixtures; the baseline worker ASR is about 45.8% (harness-program CT-18 @ b61af8f).
  - `http_post` posts to any URL with no web_guard (`orchestration/tools/web.py:51-81 @ 1cc2043`), and the frontdoor role's web category holds both web_search and http_post. The role-permission fix is the open TOOLPERM-DENY-DEFAULT in engineering-hygiene-backlog, which is not duplicated here.
  - No test checks whether untrusted values are interpolated into delegated instructions.
- **Evidence**:
  - A tool-output Sanitizer reached ASR 0.00 on GPT-4o AgentDojo against static attacks, and 30.0% against its own adaptive stage (intake-2927).
  - A trained 8B filter with released weights (intake-2933).
  - Guardrail quality depends on model size (intake-2932).
  - Adaptive attacks broke all eight defenses tested (intake-2931).
  - CaMeL guarantees do not compose across delegation (intake-2928 claims 0-1).
- **Opportunity**: AEI-CT18-ARMD-PREP and AEI-CT18-ARMD-RUN; AEI-BOUNDARY-LAUNDER-LINT; AEI-HTTPPOST-GUARD.
- **Benefit direction**: lower static-attack ASR at bounded utility loss. All wording stays "static-attack ASR on fixture set IB2" (CT-20).
- **Device lens**:
  - D-1 is prefill-heavy with a short output, so it is cheap on the CPU host.
  - D-2 regenerates the full tool output, so decode cost scales with output length. It fits the MI210 (8B), so place it there.
  - The GGUF conversion is a build cost.
- **Six controls (run)**:
  1. Frozen input: IB2 24x3 fixture digest.
  2. Baseline: arms A-C.
  3. Per-item outputs: per-arm results JSONL.
  4. Holdout: the Skill-Inject family is held out from prompt tuning.
  5. Denominator: invalid outputs count as failures, and the valid-output rate is reported.
  6. Rule: see the stop rule below.
- **Stop rule**:
  - Question: does D-1 or D-2 cut static ASR below arms A-C without dropping clean task_ok by more than 5 points?
  - Checkpoint after the worker role.
  - Futility: stop if both arms leave ASR within 5 points of arm A.
  - Answer: a lower ASR opens M6, the adaptive arm.
- **Inference fields (Stage 4)**: `· model Qwen3.6-35B-A3B worker and Qwen3.8-27B architect (CT-18 roles) plus DataFilter-8B GGUF · harness CT-18 fixture harness · metric ASR (lower better), task_ok (higher better), false-removal (lower better) · region worker per CT-18 substrate split, DataFilter on MI210 · est from CT-18.1 timings`.

### P5 — kb-search breadcrumb encoding

- **Project decision**: is kb-search recall limited by chunks that lose their document context?
- **Pinned gap**:
  - The encoded text is the section body only (`src/retrieval/kb_rag.py:663, 808 @ 1cc2043`). The breadcrumb is metadata.
  - Paragraph sub-chunks of long sections carry no heading.
  - K7 measures recall@3/5/10 on a 70-case pool.
  - The K11 lexical leg showed no uplift.
- **Evidence**:
  - On GTE-ModernColBERT (EPYC's encoder family), untrained late chunking is a null (-0.3 nDCG@10). The LLM-prefix pipeline costs about 120x the index time, and LLM prefixes with ColBERT are untested (intake-2924 claims 0-2).
  - Structure-following chunks already capture most of the gain, and in-corpus and in-document results can reverse (intake-2936).
  - The dense-only numbers in intake-2912 do not transfer directly.
- **Opportunity**: build a side index with a zero-LLM path-plus-breadcrumb prefix.
- **Six controls**:
  1. Frozen input: K7 70-case pool and corpus snapshot digest.
  2. Baseline: the production index.
  3. Per-item outputs: per-case top-10 lists.
  4. Holdout: the in-document subset is built after the arm is fixed.
  5. Denominator: all 70 cases, with misses counted.
  6. Rule: see the stop rule below.
- **Stop rule**:
  - Keep only if recall@10 rises by more than the 2-point K7 noise band without the in-document subset falling.
  - Drop if the change is inside the band.
  - Production stays unchanged either way.
- **Inference fields (Stage 4)**: `· model GTE-ModernColBERT (ONNX, CPU) · harness scripts/kb_rag/eval_k7.py · metric recall@10 (higher better) · region CPU quarter · est from the K7 build (18,010 chunks)`.
- **Broader trigger (M5)**: an LLM-written prefix arm, and the InSeNT-trained encoder (gated on its NanoBEIR regression from 67.7 to 59.2), only if this ends keep.

## Monitors and knowledge-only closures (durable prose, no checkbox)

| Packet | Closure | Owner |
|---|---|---|
| K1 | Coordination covered by existing invariants and bus practice | coordinator / harness-program |
| K2 | Long runs and context covered by existing boxes | harness-program, context-and-token-economy |
| K4 | Task and grader validity covered by EV-19 and oracle builders | eval-tower-program |
| K5 | Retrieval and thinking budget covered by K11, K7, TB-1/E-2 | knowledge-pipelines, context-and-token-economy |
| K6 | Injection claim wording covered by CT-20, CT-17, CM-3 | harness-program |
| K7 | Reviewer calibration and fresh context covered | reviewer-control-plane |
| M1 | Monitor: cross-session incident from an unverifiable completion claim | coordinator / harness-program |
| M2 | Monitor: first persisted agentic trajectory or scaffold comparison in the tower | eval-tower-program |
| M3 | Monitor: plan-first REPL mode proposed | harness-program |
| M4 | Monitor: consult-larger-model routing spec written | routing-program |
| M5 | Monitor: AEI-KB-BREADCRUMB-AB ends keep | knowledge-pipelines |
| M6 | Monitor: arm D static ASR below arms A-C | harness-program |
| M7 | Monitor: RM-3 opens, C-CRAB saturates, or a reviewer training lane with a verifiable reward exists | reviewer-control-plane |
| M8 | Monitor: REPL tool-description or tool-set change proposed | harness-program |

- **K1** coordination: covered by single writer (agents/shared/INVARIANTS.md), per-session worktrees, bus drain at boundaries, fetch-before-commit and the When NOT to fan out exceptions.
- **K2** long runs and context: covered by PREFIX-CACHE-LAYOUT-AB, CF-AKV-0, TOC-CMP-4, CF-AM-1, REPL-EMB-CONSUMER-GATE and done_when checks.
- **K4** task and grader validity: covered by EV-19 gold self-check, the oracle builders and the instrument-identity rules.
- **K5** retrieval and thinking budget: covered by the K11 lexical sweep, K7 recall@k and TB-1/E-2.
- **K6** injection claim wording: covered by CT-20, CT-17 and CM-3.
- **K7** reviewer calibration and fresh context: covered by reviewer-calibration-accounting and RA-13a.
- **Monitors, each with an observable trigger**:
  - M1: a cross-session incident caused by an unverifiable completion claim (owner: coordinator / harness-program).
  - M2: the first persisted agentic trajectory or scaffold comparison in the tower (eval-tower-program).
  - M3: a plan-first REPL mode is proposed (harness-program).
  - M4: a consult-larger-model routing spec is written (routing-program).
  - M5: AEI-KB-BREADCRUMB-AB ends keep (knowledge-pipelines).
  - M6: arm D static ASR falls below arms A-C (harness-program).
  - M7: RM-3 opens, C-CRAB saturates, or a reviewer training lane with a verifiable reward exists (reviewer-control-plane).
  - M8: a REPL tool-description change is proposed (harness-program).

## Proposed handoff edits (Stage 4 only, after approval)

Each box is written with `python3 scripts/handoffs/handoff_box.py add`. Each box below is the exact text
the dry run rendered on 2026-11-24, and it lands at the bottom of its track's `### Backlog`. The tool
creates that heading for the eval-tower, reviewer and knowledge-pipelines tracks, which have none. Every
box gets a brief (`--brief --brief-author intake`) with the `where` and `approach` given here, and its
acceptance is the done-when.

**handoffs/active/harness-program.md, track agentic-serving-harness-fixes**
```
- [ ] **AEI-CHAT-FINISH-REASON** [non-inference] Carry the backend completion_reason into the /chat response as finish_reason plus a truncated flag, so a length-cut answer is returned marked truncated instead of as a complete final answer (intake-2907 discovery; gap at src/api/models/responses.py @ 1cc2043, no finish_reason field).
      · done when: cd /mnt/raid0/llm/epyc-orchestrator && python -m pytest tests/unit/test_chat_finish_reason.py -q passes, covering stop, length and context_limit
      · gate: none        · inputs: `repos/epyc-orchestrator/src/api/models/responses.py` `repos/epyc-orchestrator/src/backends/llama_server.py`
- [ ] **AEI-TRUNC-NOTICE** [non-inference] Make the three '[... truncated at N chars]' markers in src/llm_primitives/primitives.py say how to get the rest (the spilled file path with peek/grep, or a narrower request), matching the REPL spill footer (intake-2911 claim 1).
      · done when: cd /mnt/raid0/llm/epyc-orchestrator && python -m pytest tests/unit/test_truncation_notice.py -q passes and grep -c 'truncated at' src/llm_primitives/primitives.py shows every marker carries a narrowing hint
      · gate: none        · inputs: `repos/epyc-orchestrator/src/llm_primitives/primitives.py` `repos/epyc-orchestrator/src/repl_environment/environment.py`
```
- Brief, AEI-CHAT-FINISH-REASON: where `epyc-orchestrator:src/api/models/responses.py`,
  `src/api/routes/chat.py`, `src/backends/llama_server.py`. Approach: thread completion_reason to the
  response model; map length and context_limit to `truncated=true`; never rewrite the answer text.
  New test: `tests/unit/test_chat_finish_reason.py`.
- Brief, AEI-TRUNC-NOTICE: where `epyc-orchestrator:src/llm_primitives/primitives.py::1267,1409,1529`.
  Approach: reuse the spill footer wording; if the output was spilled, name the file, otherwise ask for
  a narrower request. New test: `tests/unit/test_truncation_notice.py`.

**handoffs/active/eval-tower-program.md, track scoring-infra-standardization**
```
- [ ] **AEI-DROPS-MANIFEST** [non-inference] Emit a drops manifest (n scheduled, n scored, n dropped by reason) and graded_fraction = n_scored / n_attempted per arm with every eval-tower aggregate beside EV-18's ITT fields, and flag a quality delta whose two arms' graded fractions differ by more than 5 points (intake-2921 claims 0-1, intake-2935).
      · done when: cd /mnt/raid0/llm/epyc-orchestrator && python -m pytest tests/unit/test_eval_tower_drops_manifest.py -q passes, including a fixture where unequal graded fractions raise the flag
      · gate: none        · inputs: `repos/epyc-orchestrator/scripts/autopilot/eval_tower.py` `repos/epyc-orchestrator/scripts/benchmark/debug_scorer.py`
- [ ] **AEI-TOKEN-SPAN-RATIO** [non-inference] Check orchestrator token accounting for nested-span double counting: for one stored run per serving path (CPU llama-server role, MI210 role, streaming), compare summed per-call tokens against root-request tokens and record the ratio, fixing the aggregation if any ratio is not 1.0 (intake-2921 claim 2).
      · done when: progress/2026-11 note or handoff sub-bullet records the all-span/root-span token ratio for each of the three paths, and any ratio other than 1.0 has a linked fix commit
      · gate: none        · inputs: `repos/epyc-orchestrator/src/backends/llama_server.py`
- [ ] **AEI-RERUN-ARM-OD** [operator-decision] Decide whether measurement/protocols/quality-eval.md P-AB-1 and P-PAIRED add a same-configuration rerun arm and report the rerun flip rate beside any scaffold, harness or reviewer-arm effect (intake-2934: reruns flipped 13% of tasks at the median, as many as a harness swap).
      · done when: operator decision recorded in this box's tick verdict, and if adopted a ratified protocol amendment exists
      · gate: none        · inputs: `measurement/protocols/quality-eval.md`
```
- Brief, AEI-DROPS-MANIFEST: where `epyc-orchestrator:scripts/autopilot/eval_tower.py::EvalTower._aggregate`.
  Approach: derive the manifest from existing counters next to `itt_denominator`; set the flag
  threshold to 5 points.
- Brief, AEI-TOKEN-SPAN-RATIO: where `epyc-orchestrator:src/backends/llama_server.py` and the serving_calls
  recorder. Approach: read-only comparison on stored runs.

**handoffs/active/reviewer-control-plane.md, track reviewer-model-ablations**
```
- [ ] **AEI-REV-FLIPS** [non-inference] Add per-arm fix and break counts (worker-wrong to reviewer-reject, worker-right to reviewer-reject) and a Kamoi-style fairness line (initial-prompt strength, no oracle stop, matched-token baseline present or absent) to the RM-2 arm report, computed offline from decisions already in the review ledger (intake-2930 claims 1-2, intake-2929 claim 4).
      · done when: cd /mnt/raid0/llm/epyc-orchestrator && python -m pytest tests/unit/test_reviewer_calibration_flips.py -q passes and the RM-2 report for the A1 48-row slice prints the new columns
      · gate: none        · inputs: `repos/epyc-orchestrator/scripts/analysis/reviewer_calibration_report.py`
- [ ] **AEI-REV-A1-PRECHECK** [non-inference] Record two facts about the A1 self-review runner before any further A1 arm: whether the worker patch reaches the reviewer as user-role or assistant-role content, and whether the C-CRAB rows of the 48-row slice carry a gold defect location usable as an oracle hint (intake-2939, intake-2940).
      · done when: a sub-bullet under this box names the runner file:line for the message role and the count of the 48 rows with a gold defect location
      · gate: none
- [ ] **AEI-REV-A1-LOCATE-PROBE** [inference] Run one bounded diagnostic on the 48-row A1 slice with the incumbent A1 reviewer: arm L gives the gold defect location, arm P uses a comprehensive single-pass review prompt; report FA, FR and AUC per arm against the A1 baseline, then close A1 as a negative control unless arm L lifts (intake-2940 claims, intake-2937).
      · done when: verdict tick records FA/FR/AUC for arms L and P on the 48 rows with the pass/close decision under the stop rule
      · gate: AEI-REV-A1-PRECHECK
      · model Qwen3.5-122B (incumbent A1) · build production-consolidated-v10 · harness RM-2 runner · metric FA/FR lower, AUC higher · region CPU host quarter · est ~2200 s per arm from the A1 48-row run
      · stop rule: question = does location (L) or a comprehensive prompt (P) lift A1; n=48 resolves AUC +0.15 or FA+FR -20 pts; checkpoint 24 rows; futility if L not better than A1 on FA+FR at 24; answer routes to M7 (L lifts) or closes A1 (neither)
```
- The last two continuation lines of the probe box are hand-added in the same grammar, because
  `handoff_box.py add` has no inference-field flags.
- Brief, AEI-REV-FLIPS: where `epyc-orchestrator:scripts/analysis/reviewer_calibration_report.py`. New
  test: `tests/unit/test_reviewer_calibration_flips.py`.

**handoffs/active/harness-program.md, track harness-improvement-loop**
```
- [ ] **AEI-CT18-ARMD-PREP** [non-inference] Prepare CT-18 arm D, a tool-output sanitizer in front of the agent: D-1 a detect-and-extract guardrail prompt run on the local worker role, D-2 the released DataFilter Llama-3.1-8B weights converted to GGUF with its special tokens checked, both given the trusted task and applied per JSON key (intake-2927, intake-2932, intake-2933).
      · done when: fixture-harness dry run on 3 IB2 items prints D-1 and D-2 sanitized outputs, and the GGUF tokenizer test shows the DataFilter special tokens round-trip
      · gate: none
- [ ] **AEI-CT18-ARMD-RUN** [inference] Run CT-18 arms D-1 and D-2 on the IB2 24x3 fixtures with the worker and architect roles and report static-attack ASR, aligned-twin compliance, clean task_ok and clean-output false-removal rate per arm against arms A-C, worded per CT-20 (intake-2927 claims 0-3, intake-2931).
      · done when: verdict tick records ASR, aligned-twin compliance, task_ok and false-removal rate for D-1 and D-2 beside arms A-C on IB2 24x3, worded static-attack ASR on fixture set IB2
      · gate: AEI-CT18-ARMD-PREP
      · model CT-18 worker and architect roles + DataFilter-8B GGUF · harness CT-18 fixture harness · metric ASR lower, task_ok higher, false-removal lower · region CT-18 substrate split, DataFilter on MI210 · est from CT-18.1 timings
      · stop rule: question = does D-1 or D-2 cut static ASR below arms A-C with clean task_ok within 5 pts; checkpoint after the worker role; futility if both within 5 pts of arm A; answer opens M6
- [ ] **AEI-BOUNDARY-LAUNDER-LINT** [non-inference] Add a static test that flags any delegation call site where a value from the untrusted-source list (tool output, worker output, doc text, retrieved chunk, report) is interpolated into a child role's natural-language instruction instead of a separate data field (intake-2928 claims 0-1).
      · done when: cd /mnt/raid0/llm/epyc-orchestrator && python -m pytest tests/unit/test_boundary_laundering_lint.py -q passes and lists each current call site as clean or allowlisted with a reason
      · gate: none
- [ ] **AEI-HTTPPOST-GUARD** [non-inference] Apply the SEC-EXEC-3 web_guard destination check to http_post (orchestration/tools/web.py), which today posts to any URL while roles holding the web category also read untrusted pages (intake-2907 discovery; intake-2928 context).
      · done when: cd /mnt/raid0/llm/epyc-orchestrator && python -m pytest tests/unit/test_web_guard_http_post.py -q passes, refusing private and metadata destinations for http_post
      · gate: none        · inputs: `repos/epyc-orchestrator/orchestration/tools/web.py` `repos/epyc-orchestrator/src/repl_environment/web_guard.py`
```

**handoffs/active/knowledge-pipelines.md, track colbert-reranker-web-research**
```
- [ ] **AEI-KB-BREADCRUMB-AB** [inference] Build a side kb-search index whose encoded chunk text is prefixed with the file path and full heading breadcrumb, and compare it with the production index on the K7 70-case pool (recall@10) plus an in-document subset, with the production index unchanged (intake-2924 claims 0-2, intake-2936, intake-2912).
      · done when: verdict tick records recall@3/5/10 for both indexes on the K7 pool and the in-document subset with the keep/drop decision under the stop rule
      · gate: none        · inputs: `repos/epyc-orchestrator/src/retrieval/kb_rag.py` `repos/epyc-orchestrator/src/retrieval/markdown_chunker.py` `repos/epyc-orchestrator/scripts/kb_rag/eval_k7.py`
      · model GTE-ModernColBERT ONNX · harness scripts/kb_rag/eval_k7.py · metric recall@10 higher · region CPU quarter · est from the K7 build (18,010 chunks)
      · stop rule: keep only if recall@10 rises more than the 2-pt K7 noise band and the in-document subset does not fall; drop inside the band; production index unchanged either way
```
- That track is the only track in knowledge-pipelines.md. Its ColBERT retrieval scope is the nearest
  fit for kb-search. The operator may prefer a new `## Track: kb-search` (open question Q2).

## Index rows

No new handoff, so no domain-index row. **Master index operator queue**, one row (prepared, not
applied):

```
| AEI-RERUN-ARM-OD | Add a same-configuration rerun arm and rerun flip rate to quality-eval P-AB-1/P-PAIRED? Options (a) all comparisons (recommended), (b) ratified-claim comparisons only, (c) no change. | [eval-tower-program.md](eval-tower-program.md) AEI-RERUN-ARM-OD | 2026-11-24 |
```

## Dive-surfaced sources

- All wave-1 surfaced sources were ingested and dived in wave 2, or declined with reasons recorded.
- All wave-2 surfaced sources are declined under the three-sweep authorisation. The list is in
  `sweep3-wave2-dives.md`.

## Second-reader disagreements (for the operator; nothing auto-overturned)

- The haiku second reader checked 164 claims: 113 yes, 51 partial, 0 no.
- Each "partial" claim adds a count, condition or mechanism from elsewhere in the same source beyond its
  single anchor quote. Every number this plan cites appears in its own anchor quote or in the entry's
  reported_results from the dive.

## Open questions for the operator

1. Approve the five packets as drafted?
2. Should P5 live in the existing colbert-reranker-web-research track, or in a new kb-search track?
3. Decide AEI-RERUN-ARM-OD. Option (a) is recommended.

## Steering ledger

There is one row: the operator's authorisation, recorded verbatim with disposition context-only.

## Complete recommendation mapping

| Ledger row | Source or review | Retained recommendation | Terminal plan mapping |
|---|---|---|---|
| S1-1 | intake-2907 pp.43-44 (discovery) + grounding Q1 | Truncated or declined generations must not be returned as complete answers | P1 / AEI-CHAT-FINISH-REASON |
| S1-2 | intake-2907 pp.22-23, 75 (discovery) + grounding Q2 | Keep the prompt prefix byte-stable for prefix/KV cache hits | K2 (covered by existing work) |
| S1-3 | intake-2907 pp.39-41 + intake-2911 claim 1 + grounding Q3 | Tool failures and truncation reach the model as instructive observations | P1 / AEI-TRUNC-NOTICE |
| S1-4 | intake-2907 p.78 + intake-2909 claim 3 | Elide old tool results in long runs | K2 (covered by existing work) |
| S1-5 | intake-2914 claims 0-1 | Do not trust a review step that has no new evidence | P3 / AEI-REV-FLIPS |
| S1-6 | intake-2910, intake-2921, intake-2934 | Eval statistics: graded fraction, rerun noise, pass^k | P2 / AEI-DROPS-MANIFEST |
| S1-7 | intake-2912, intake-2924 | kb-search document-situating context | P5 / AEI-KB-BREADCRUMB-AB |
| S1-8 | intake-2907 p.139 (discovery) + grounding Q8 | Untrusted reading and external sending in one role | P4 / AEI-HTTPPOST-GUARD |
| S1-9 | intake-2908 claims 0-4 | Goal list with verified pass status for long-running sessions | K2 (covered by existing work) |
| i2908-A1 | intake-2908 claims 3-4 | Premature-pass check in agent loop protocol | K2 (covered by existing work) |
| i2908-A2 | intake-2908 claim 2 | A/B JSON versus Markdown for model-mutated state | K2 knowledge-only |
| i2909-A1 | intake-2909 claim 3 | Tool-result-clearing arm in the compaction A/B | K2 (covered by existing work) |
| i2909-A2 | intake-2909 claim 2 | Hybrid up-front plus just-in-time retrieval for REPL agents | K2 (covered by existing work) |
| i2910-A1 | intake-2910 claim 3 | Reference-solution check and 0%-over-N task audit | K4 (covered by existing work) |
| i2910-A2 | intake-2910 claim 4 + intake-2922 claim 3 | Report pass^k beside pass@1 | M2 (monitor) |
| i2910-A3 | intake-2910 claims 0, 4 | Grade outcome first; capability vs regression tags | K4 knowledge-only |
| i2910-A4 | intake-2910 (graders table) | Calibrate LLM-judge graders on human labels | K4 (covered by existing work) |
| i2911-A1 | intake-2911 claim 0 | Tool-eval harness with held-out split | M8 (monitor) |
| i2911-A2 | intake-2911 claims 1-2 | response_format and narrowing truncation messages | P1 / AEI-TRUNC-NOTICE |
| i2911-A3 | intake-2911 claim 3 | Namespacing A/B on local models | M8 (monitor) |
| i2912-A1 | intake-2912 claims 0-2 | Contextual prefix on kb-search | P5 / AEI-KB-BREADCRUMB-AB |
| i2912-A2 | intake-2912 claim 1 | BM25 leg with rank fusion | K5 (covered by existing work) |
| i2912-A3 | intake-2912 claim 4 | Sweep chunk count k for local readers | K5 knowledge-only |
| i2913-A1 | intake-2913 claims 0-1 | Provenance tags plus policy check on one tool class | M3 (monitor) |
| i2913-A2 | intake-2913 claim 3 | Measure the token multiplier before a P/Q split | M3 (monitor) |
| i2913-A3 | intake-2913 (Q-LLM cost) | Quarantined LLM on a small local model | M3 (monitor) |
| i2913-A4 | intake-2913 claim 2 | Never claim provable security without the interpreter | K6 (covered by existing work) |
| i2914-A1 | intake-2914 claims 0-1 | A no-evidence review step is advisory unless an A/B wins | P3 / AEI-REV-A1-LOCATE-PROBE |
| i2914-A2 | intake-2914 (answer-change analysis) | Change matrix per review step | P3 / AEI-REV-FLIPS |
| i2914-A3 | intake-2914 claim 3 | Route escalation to evidence-bearing checks | K7 (covered by existing work) |
| i2914-A4 | intake-2914 (scope) | One bounded probe on our reviewer before treating as fact | P3 / AEI-REV-A1-LOCATE-PROBE |
| i2915-A1 | intake-2915 claims 1, 4 | Reasoning-effort prior tested with 3+ trials | K5 (covered by existing work) |
| i2915-A2 | intake-2915 claim 2 | Cost axes per eval cell (tokens, wall-seconds) | M2 (monitor) |
| i2915-A3 | intake-2915 claim 3 | LLM-aided log inspection on agent runs | M2 (monitor) |
| i2915-A4 | intake-2915 (surfaced) | Dive 2611.04399 and 2602.16666 | K5 knowledge-only (discharged) |
| i2915-A5 | intake-2915 (A3 limitations) | Record weights hash and quant per eval row | K4 (covered by existing work) |
| i2916-A1 | intake-2916 claims 0-1 | Single-writer delegation rule | K1 (covered by existing work) |
| i2916-A2 | intake-2916 claim 2 | Small summariser model for compaction | K2 (covered by existing work) |
| i2917-A1 | intake-2917 claim 4 | Checkable evidence on bus completion claims | M1 (monitor) |
| i2917-A2 | intake-2917 (first-turn plan) | First-turn plan with paths on cross-session handoffs | M1 (monitor) |
| i2917-A3 | intake-2917 claim 4 | Shared record of semantic interface decisions | M1 (monitor) |
| i2917-A4 | intake-2917 claims 1-2 | Solo-first prior in fan-out rules | K1 (covered by existing work) |
| w1a-A1 | intake-2918 claims 1-2 | Clean-context reviewer with builder-side filter | K7 (covered by existing work) |
| w1a-A2 | intake-2918 claim 3 | Consult design forks full context | M4 (monitor) |
| w1a-A3 | intake-2918 claim 0 | Cross-reference the single-writer rule | K1 knowledge-only |
| w1e-A1 | intake-2919 claims 2-3 | Larger model opens worker/architect exchanges | M4 (monitor) |
| w1e-A2 | intake-2919 claim 4 | Capable session states the reference frame first | M1 (monitor) |
| w1e-A3 | intake-2919 claim 0 | Collaboration-aware eval for small collaborating models | M4 (monitor) |
| w1f-A1 | intake-2920 claim 0 | Staleness check at bus task boundaries | K1 (covered by existing work) |
| w1f-A2 | intake-2920 claim 2 | Assistance-seeking metric | M1 (monitor) |
| w1f-A3 | intake-2920 claim 4 | Stuck detection in code, not agent budgets | K1 knowledge-only |
| w1g-A1 | intake-2921 claims 0-1 | Graded-fraction column and imbalance flag | P2 / AEI-DROPS-MANIFEST |
| w1g-A2 | intake-2921 claim 3 | Provenance tag on trace actions | M2 (monitor) |
| w1g-A3 | intake-2921 claim 2 | All-span vs root-span token ratio | P2 / AEI-TOKEN-SPAN-RATIO |
| w1g-A4 | intake-2921 claims 0-2 | Treat HAL cost and Generalist numbers as suspect | K5 knowledge-only |
| w1h-A1 | intake-2922 claim 3 | Outcome and resource consistency from repeated records | K7 (covered by existing work) |
| w1h-A2 | intake-2922 (predictability) | ECE, AUROC, Brier from stored confidence | K7 (covered by existing work) |
| w1h-A3 | intake-2922 (K=5 temp 0) | Check byte-identical repeats before trusting consistency | K4 (covered by existing work) |
| w1h-A4 | intake-2922 claim 4 | Prompt-paraphrase robustness probe | M2 (monitor) |
| w1h-A5 | intake-2922 claim 0 | Adopt the aggregate reliability score | decline: the paper itself calls its aggregation subjective; EPYC claim grammar is per metric |
| w1b-A1 | intake-2923 claim 1 | Ablate prefix, BM25 and rerank separately | P5 / AEI-KB-BREADCRUMB-AB |
| w1c-A1 | intake-2924 claim 0 | Untrained late chunking on GTE-ModernColBERT | decline: measured -0.3 nDCG@10 on the same encoder family |
| w1c-A2 | intake-2924 claims 0-2 | Zero-LLM breadcrumb prefix A/B | P5 / AEI-KB-BREADCRUMB-AB |
| w1c-A3 | intake-2924 claim 1 + intake-2912 | LLM-written prefix if breadcrumb lifts | M5 (monitor) |
| w1c-A4 | intake-2924 claim 3 | InSeNT trained embedder | M5 (monitor) |
| w1d-A1 | intake-2925 | Record late chunking as a measured null on ColBERT | K5 knowledge-only |
| w1d-A2 | intake-2925 claim 0 | Late chunking for a future dense component | decline: no dense retriever consumer exists |
| w1i-A1 | intake-2926 claim 1 | Tiered-risk naming note | K6 knowledge-only |
| w1i-A2 | intake-2926 claims 1-2 | Prompt screening, output auditing, plan-template caching | decline: the source has no measurement |
| w1j-A1 | intake-2927 claims 0-3 | CT-18 arm D tool-output sanitizer | P4 / AEI-CT18-ARMD-RUN |
| w1j-A2 | intake-2927 claim 3 | Second-order semantic attack templates | M6 (monitor) |
| w1j-A3 | intake-2927 claim 2 | Use AgentDojo-Revised if imported | K6 knowledge-only |
| w1k-A1 | intake-2928 claims 0-1 | Boundary-laundering static check | P4 / AEI-BOUNDARY-LAUNDER-LINT |
| w1k-A2 | intake-2928 claim 3 | Fixed-plan fraction of REPL tool chains | M3 (monitor) |
| w1k-A3 | intake-2928 claim 4 | Return schemas in REPL tool descriptions | K6 (covered by existing work) |
| w1l-A1 | intake-2929 claims 1, 4 | Fair-evaluation checklist on reviewer arms | P3 / AEI-REV-FLIPS |
| w1l-A2 | intake-2929 claim 1 | A1 stays a negative control | P3 / AEI-REV-A1-LOCATE-PROBE |
| w1l-A3 | intake-2929 claim 2 | Gate feedback into a worker retry | M7 (monitor) |
| w1l-A4 | intake-2929 claim 3 | Decomposed per-claim verifier arm | M7 (monitor) |
| w1m-A1 | intake-2930 claims 0-1 | Fix and break rates per arm | P3 / AEI-REV-FLIPS |
| w1m-A2 | intake-2930 claim 2 | SFT on self-review traces | decline: the source's SFT controls gave delta at most +1.8 or negative (behaviour collapse) |
| w1m-A3 | intake-2930 claims 0, 4 | RL self-correction feasibility note | M7 (monitor) |
| w1m-A4 | intake-2930 claim 3 | Keep A1 as status-quo anchor | P3 / AEI-REV-A1-LOCATE-PROBE |
| w2a-A1 | intake-2931 | Adaptive-attack arm and cross-evaluation grid | M6 (monitor) |
| w2a-A2 | intake-2931 | Valid-output rate and utility beside ASR | P4 / AEI-CT18-ARMD-RUN |
| w2b-A1 | intake-2932 | Arm D-1 detect-and-extract guardrail | P4 / AEI-CT18-ARMD-PREP |
| w2b-A2 | intake-2932 | Injection-definition prompt ablation | P4 / AEI-CT18-ARMD-PREP |
| w2c-A1 | intake-2933 | Arm D-2 DataFilter weights via GGUF | P4 / AEI-CT18-ARMD-PREP |
| w2c-A2 | intake-2933 | Filter sees trusted task; false-removal rate | P4 / AEI-CT18-ARMD-RUN |
| w2f-A1 | intake-2936 | Structure baseline plus in-corpus and in-document metrics | P5 / AEI-KB-BREADCRUMB-AB |
| w2f-A2 | intake-2936 | LumberChunker or proposition chunking | decline: no in-corpus gain over paragraph chunking at about 1000x lower throughput (source Table 3) |
| w2d-A1 | intake-2934 | Rerun arm plus discordance-based MDE | P2 / AEI-RERUN-ARM-OD |
| w2d-A2 | intake-2934 | Decompose harness token cost | M2 (monitor) |
| w2e-A1 | intake-2935 | Drops manifest plus named reporting rule | P2 / AEI-DROPS-MANIFEST |
| w2e-A2 | intake-2935 | Re-grade reviewer rollouts under an alternative rule | M7 (monitor) |
| w2g-A1 | intake-2937 | Comprehensive-prompt arm before multi-reviewer arms | P3 / AEI-REV-A1-LOCATE-PROBE |
| w2g-A2 | intake-2937 | Known-bug reviewer corpus from repo history | M7 (monitor) |
| w2h-A1 | intake-2938 | Wait-continuation arm on A1 | decline: source has no correct-trace control and A1 AUC is near chance; reopen only if the location arm lifts |
| w2i-A1 | intake-2939 | Check message role of the worker patch in the A1 runner | P3 / AEI-REV-A1-PRECHECK |
| w2i-A2 | intake-2939 | Role-relabel arm on A1 | decline: flagging-only gains, needs the error location, false positives untested by the authors |
| w2j-A1 | intake-2940 | Oracle defect-location arm on A1 | P3 / AEI-REV-A1-LOCATE-PROBE |
| w2k-A1 | intake-2941 | RISE-style self-correction fine-tuning | M7 (monitor) |

## Stage-3 filing payload

```json
{
 "format_version": 2,
 "entry_updates": [
  {
   "id": "intake-2907",
   "integration_disposition": "knowledge_only",
   "handoffs_updated": [],
   "handoffs_created": [],
   "disposition_evidence": [
    "Textbook synthesis; its claims were routed through the dived references (intake-agents-intro-20261124 Stage-3 plan)"
   ]
  },
  {
   "id": "intake-2908",
   "integration_disposition": "knowledge_only",
   "handoffs_updated": [],
   "handoffs_created": [],
   "disposition_evidence": [
    "Covered by done_when checks and autopilot startup gates (K2) (intake-agents-intro-20261124 Stage-3 plan)"
   ]
  },
  {
   "id": "intake-2909",
   "integration_disposition": "knowledge_only",
   "handoffs_updated": [],
   "handoffs_created": [],
   "disposition_evidence": [
    "Covered by the compaction A/B boxes (K2) (intake-agents-intro-20261124 Stage-3 plan)"
   ]
  },
  {
   "id": "intake-2910",
   "integration_disposition": "knowledge_only",
   "handoffs_updated": [],
   "handoffs_created": [],
   "disposition_evidence": [
    "Covered by EV-19 and the eval-tower Pass^k monitor (K4, M2) (intake-agents-intro-20261124 Stage-3 plan)"
   ]
  },
  {
   "id": "intake-2911",
   "integration_disposition": "integrated",
   "handoffs_updated": [
    "harness-program.md"
   ],
   "handoffs_created": [],
   "disposition_evidence": [
    "Routed to approved boxes in harness-program.md (intake-agents-intro-20261124 Stage-3 plan)"
   ]
  },
  {
   "id": "intake-2912",
   "integration_disposition": "integrated",
   "handoffs_updated": [
    "knowledge-pipelines.md"
   ],
   "handoffs_created": [],
   "disposition_evidence": [
    "Routed to approved boxes in knowledge-pipelines.md (intake-agents-intro-20261124 Stage-3 plan)"
   ]
  },
  {
   "id": "intake-2913",
   "integration_disposition": "monitor",
   "handoffs_updated": [],
   "handoffs_created": [],
   "disposition_evidence": [
    "M3: trigger is a proposed plan-first REPL mode (intake-agents-intro-20261124 Stage-3 plan)"
   ]
  },
  {
   "id": "intake-2914",
   "integration_disposition": "integrated",
   "handoffs_updated": [
    "reviewer-control-plane.md"
   ],
   "handoffs_created": [],
   "disposition_evidence": [
    "Routed to approved boxes in reviewer-control-plane.md (intake-agents-intro-20261124 Stage-3 plan)"
   ]
  },
  {
   "id": "intake-2915",
   "integration_disposition": "knowledge_only",
   "handoffs_updated": [],
   "handoffs_created": [],
   "disposition_evidence": [
    "Covered by TB-1/E-2; cost axes under M2 (intake-agents-intro-20261124 Stage-3 plan)"
   ]
  },
  {
   "id": "intake-2916",
   "integration_disposition": "knowledge_only",
   "handoffs_updated": [],
   "handoffs_created": [],
   "disposition_evidence": [
    "Covered by single-writer invariants (K1) (intake-agents-intro-20261124 Stage-3 plan)"
   ]
  },
  {
   "id": "intake-2917",
   "integration_disposition": "monitor",
   "handoffs_updated": [],
   "handoffs_created": [],
   "disposition_evidence": [
    "M1: trigger is a cross-session incident from an unverifiable completion claim (intake-agents-intro-20261124 Stage-3 plan)"
   ]
  },
  {
   "id": "intake-2918",
   "integration_disposition": "knowledge_only",
   "handoffs_updated": [],
   "handoffs_created": [],
   "disposition_evidence": [
    "Covered by RA-13a; consult ideas under M4 (intake-agents-intro-20261124 Stage-3 plan)"
   ]
  },
  {
   "id": "intake-2919",
   "integration_disposition": "monitor",
   "handoffs_updated": [],
   "handoffs_created": [],
   "disposition_evidence": [
    "M4: trigger is a consult-larger-model routing spec (intake-agents-intro-20261124 Stage-3 plan)"
   ]
  },
  {
   "id": "intake-2920",
   "integration_disposition": "knowledge_only",
   "handoffs_updated": [],
   "handoffs_created": [],
   "disposition_evidence": [
    "Covered by bus drain and fetch-before-commit (K1) (intake-agents-intro-20261124 Stage-3 plan)"
   ]
  },
  {
   "id": "intake-2921",
   "integration_disposition": "integrated",
   "handoffs_updated": [
    "eval-tower-program.md"
   ],
   "handoffs_created": [],
   "disposition_evidence": [
    "Routed to approved boxes in eval-tower-program.md (intake-agents-intro-20261124 Stage-3 plan)"
   ]
  },
  {
   "id": "intake-2922",
   "integration_disposition": "monitor",
   "handoffs_updated": [],
   "handoffs_created": [],
   "disposition_evidence": [
    "M2: trigger is the first persisted agentic trajectory in the tower (intake-agents-intro-20261124 Stage-3 plan)"
   ]
  },
  {
   "id": "intake-2923",
   "integration_disposition": "integrated",
   "handoffs_updated": [
    "knowledge-pipelines.md"
   ],
   "handoffs_created": [],
   "disposition_evidence": [
    "Routed to approved boxes in knowledge-pipelines.md (intake-agents-intro-20261124 Stage-3 plan)"
   ]
  },
  {
   "id": "intake-2924",
   "integration_disposition": "integrated",
   "handoffs_updated": [
    "knowledge-pipelines.md"
   ],
   "handoffs_created": [],
   "disposition_evidence": [
    "Routed to approved boxes in knowledge-pipelines.md (intake-agents-intro-20261124 Stage-3 plan)"
   ]
  },
  {
   "id": "intake-2925",
   "integration_disposition": "declined",
   "handoffs_updated": [],
   "handoffs_created": [],
   "disposition_evidence": [
    "Superseded for ColBERT by intake-2924; measured null (intake-agents-intro-20261124 Stage-3 plan)"
   ]
  },
  {
   "id": "intake-2926",
   "integration_disposition": "declined",
   "handoffs_updated": [],
   "handoffs_created": [],
   "disposition_evidence": [
    "Position paper with no measurement and a broken CaMeL citation (intake-agents-intro-20261124 Stage-3 plan)"
   ]
  },
  {
   "id": "intake-2927",
   "integration_disposition": "integrated",
   "handoffs_updated": [
    "harness-program.md"
   ],
   "handoffs_created": [],
   "disposition_evidence": [
    "Routed to approved boxes in harness-program.md (intake-agents-intro-20261124 Stage-3 plan)"
   ]
  },
  {
   "id": "intake-2928",
   "integration_disposition": "integrated",
   "handoffs_updated": [
    "harness-program.md"
   ],
   "handoffs_created": [],
   "disposition_evidence": [
    "Routed to approved boxes in harness-program.md (intake-agents-intro-20261124 Stage-3 plan)"
   ]
  },
  {
   "id": "intake-2929",
   "integration_disposition": "integrated",
   "handoffs_updated": [
    "reviewer-control-plane.md"
   ],
   "handoffs_created": [],
   "disposition_evidence": [
    "Routed to approved boxes in reviewer-control-plane.md (intake-agents-intro-20261124 Stage-3 plan)"
   ]
  },
  {
   "id": "intake-2930",
   "integration_disposition": "integrated",
   "handoffs_updated": [
    "reviewer-control-plane.md"
   ],
   "handoffs_created": [],
   "disposition_evidence": [
    "Routed to approved boxes in reviewer-control-plane.md (intake-agents-intro-20261124 Stage-3 plan)"
   ]
  },
  {
   "id": "intake-2931",
   "integration_disposition": "integrated",
   "handoffs_updated": [
    "harness-program.md"
   ],
   "handoffs_created": [],
   "disposition_evidence": [
    "Routed to approved boxes in harness-program.md (intake-agents-intro-20261124 Stage-3 plan)"
   ]
  },
  {
   "id": "intake-2932",
   "integration_disposition": "integrated",
   "handoffs_updated": [
    "harness-program.md"
   ],
   "handoffs_created": [],
   "disposition_evidence": [
    "Routed to approved boxes in harness-program.md (intake-agents-intro-20261124 Stage-3 plan)"
   ]
  },
  {
   "id": "intake-2933",
   "integration_disposition": "integrated",
   "handoffs_updated": [
    "harness-program.md"
   ],
   "handoffs_created": [],
   "disposition_evidence": [
    "Routed to approved boxes in harness-program.md (intake-agents-intro-20261124 Stage-3 plan)"
   ]
  },
  {
   "id": "intake-2934",
   "integration_disposition": "integrated",
   "handoffs_updated": [
    "eval-tower-program.md"
   ],
   "handoffs_created": [],
   "disposition_evidence": [
    "Routed to approved boxes in eval-tower-program.md (intake-agents-intro-20261124 Stage-3 plan)"
   ]
  },
  {
   "id": "intake-2935",
   "integration_disposition": "integrated",
   "handoffs_updated": [
    "eval-tower-program.md"
   ],
   "handoffs_created": [],
   "disposition_evidence": [
    "Routed to approved boxes in eval-tower-program.md (intake-agents-intro-20261124 Stage-3 plan)"
   ]
  },
  {
   "id": "intake-2936",
   "integration_disposition": "integrated",
   "handoffs_updated": [
    "knowledge-pipelines.md"
   ],
   "handoffs_created": [],
   "disposition_evidence": [
    "Routed to approved boxes in knowledge-pipelines.md (intake-agents-intro-20261124 Stage-3 plan)"
   ]
  },
  {
   "id": "intake-2937",
   "integration_disposition": "integrated",
   "handoffs_updated": [
    "reviewer-control-plane.md"
   ],
   "handoffs_created": [],
   "disposition_evidence": [
    "Routed to approved boxes in reviewer-control-plane.md (intake-agents-intro-20261124 Stage-3 plan)"
   ]
  },
  {
   "id": "intake-2938",
   "integration_disposition": "declined",
   "handoffs_updated": [],
   "handoffs_created": [],
   "disposition_evidence": [
    "Wait arm declined: no correct-trace control; A1 near chance (intake-agents-intro-20261124 Stage-3 plan)"
   ]
  },
  {
   "id": "intake-2939",
   "integration_disposition": "integrated",
   "handoffs_updated": [
    "reviewer-control-plane.md"
   ],
   "handoffs_created": [],
   "disposition_evidence": [
    "Routed to approved boxes in reviewer-control-plane.md (intake-agents-intro-20261124 Stage-3 plan)"
   ]
  },
  {
   "id": "intake-2940",
   "integration_disposition": "integrated",
   "handoffs_updated": [
    "reviewer-control-plane.md"
   ],
   "handoffs_created": [],
   "disposition_evidence": [
    "Routed to approved boxes in reviewer-control-plane.md (intake-agents-intro-20261124 Stage-3 plan)"
   ]
  },
  {
   "id": "intake-2941",
   "integration_disposition": "monitor",
   "handoffs_updated": [],
   "handoffs_created": [],
   "disposition_evidence": [
    "M7: trigger is a reviewer training lane with a verifiable reward (intake-agents-intro-20261124 Stage-3 plan)"
   ]
  }
 ],
 "opportunity_reviews": {
  "P1": {
   "project_objective": "Agent and chat answers are never silently truncated, and every truncation tells the model how to recover",
   "implementation_ref": "epyc-orchestrator @ 1cc2043: src/backends/llama_server.py:596-612, 1102-1111 (completion_reason); src/api/models/responses.py (no finish_reason); src/llm_primitives/primitives.py:1267, 1409, 1529 (markers without hints); src/repl_environment/environment.py:1008-1085 (spill footer)",
   "gap": "/chat returns a length-cut answer as final; three truncation markers give no narrowing hint",
   "operational_change": "Surface finish_reason/truncated on /chat; add narrowing hints to the three markers",
   "benefit_direction": "Fewer silent partial answers and fewer repeated full-output calls; no change to complete answers",
   "owner": "handoffs/active/harness-program.md",
   "execution_conditions": "Code change behind tests; API-only reload by the owning session; no inference",
   "closure_basis": "Immediate"
  },
  "P2": {
   "project_objective": "Eval deltas cannot be reordered by instrument errors (ungraded rows, double-counted tokens, single-run noise)",
   "implementation_ref": "EV-18 ITT fields (epyc-orchestrator ea8c7338, 3d8830ee; eval-tower-program EV-18); MEASUREMENT.md:170-184; measurement/protocols/quality-eval.md P-AB-1/P-PAIRED @ b61af8f",
   "gap": "No graded-fraction imbalance gate, no drops manifest, no proof that token accounting is single-counted, no rerun-flip control",
   "operational_change": "Drops manifest + graded-fraction flag; token span ratio check; operator decision on a rerun arm",
   "benefit_direction": "Fewer false keeps/reverts from instrument artefacts; no change to scorer semantics",
   "owner": "handoffs/active/eval-tower-program.md",
   "execution_conditions": "Zero inference for the first two boxes; the protocol change is operator-only (measurement trust boundary)",
   "closure_basis": "Immediate"
  },
  "P3": {
   "project_objective": "Reviewer arm decisions rest on fair, flip-aware comparisons, and A1 is either justified or closed",
   "implementation_ref": "reviewer-control-plane.md RM-2 @ b61af8f (A1 FA 45.8%, FR 41.7%, AUC 0.463, 48 rows); epyc-orchestrator scripts/analysis/reviewer_calibration_report.py:304-345 @ 1cc2043",
   "gap": "No fix/break counts or fairness line; no located or comprehensive-prompt arm; A1 still consumes arm budget",
   "operational_change": "Offline flip report; zero-inference precheck; one bounded two-arm probe with a closure rule",
   "benefit_direction": "Reviewer budget moves off a near-chance arm or gains a mechanism-level reason to keep it",
   "owner": "handoffs/active/reviewer-control-plane.md",
   "execution_conditions": "Precheck and flips are zero inference; the probe needs a CPU-host window booked as inference",
   "closure_basis": "Immediate"
  },
  "P4": {
   "project_objective": "Injected tool output cannot steer agents into external effects; measured defenses beyond prompt wording",
   "implementation_ref": "harness-program CT-18/CT-20/CT-21 @ b61af8f (IB2 fixtures, baseline worker ASR about 45.8%); epyc-orchestrator orchestration/tools/web.py:51-81, src/repl_environment/web_guard.py @ 1cc2043",
   "gap": "No tool-output sanitizer arm; no check for untrusted data in delegated instructions; http_post unguarded",
   "operational_change": "Arm D prep and run; boundary-laundering lint; http_post destination guard",
   "benefit_direction": "Lower static-attack ASR at bounded utility cost; wording stays static-attack only",
   "owner": "handoffs/active/harness-program.md",
   "execution_conditions": "Prep, lint and guard are zero inference; arm D run needs CPU and MI210 windows; DataFilter GGUF conversion is a build cost",
   "closure_basis": "Immediate"
  },
  "P5": {
   "project_objective": "kb-search finds the right file and passage for prior-decision lookups",
   "implementation_ref": "epyc-orchestrator src/retrieval/kb_rag.py:663, 808, 917-1062; src/retrieval/markdown_chunker.py:93-170; scripts/kb_rag/eval_k7.py @ 1cc2043; knowledge-pipelines status (K7, K11)",
   "gap": "Encoded chunk text carries no file path or breadcrumb; paragraph sub-chunks lose their heading",
   "operational_change": "Side index with breadcrumb-prefixed encoding, measured on K7 and an in-document subset",
   "benefit_direction": "Higher recall@10 without changing the production index; zero LLM cost",
   "owner": "handoffs/active/knowledge-pipelines.md",
   "execution_conditions": "CPU ColBERT encoding of a side index (inference-class compute, booked); production index untouched",
   "closure_basis": "Immediate"
  },
  "K1": {
   "project_objective": "Parallel sessions coordinate without conflicting writes",
   "implementation_ref": "see outcome reviews; pinned at b61af8f / 1cc2043",
   "gap": "none beyond existing work",
   "operational_change": "none",
   "benefit_direction": "n/a",
   "owner": "handoffs/active/harness-program.md",
   "execution_conditions": "n/a",
   "closure_basis": "Single writer, per-session worktrees, bus drain and done_when checks already implement the sources' remedies"
  },
  "K2": {
   "project_objective": "Long runs keep verified progress and a bounded context",
   "implementation_ref": "see outcome reviews; pinned at b61af8f / 1cc2043",
   "gap": "none beyond existing work",
   "operational_change": "none",
   "benefit_direction": "n/a",
   "owner": "handoffs/active/context-and-token-economy.md",
   "execution_conditions": "n/a",
   "closure_basis": "Existing boxes (PREFIX-CACHE-LAYOUT-AB, CF-AKV-0, TOC-CMP-4, CF-AM-1, REPL-EMB-CONSUMER-GATE) and done_when checks cover the actions"
  },
  "K4": {
   "project_objective": "Eval tasks and graders are valid",
   "implementation_ref": "see outcome reviews; pinned at b61af8f / 1cc2043",
   "gap": "none beyond existing work",
   "operational_change": "none",
   "benefit_direction": "n/a",
   "owner": "handoffs/active/eval-tower-program.md",
   "execution_conditions": "n/a",
   "closure_basis": "EV-19 gold self-check, oracle builders and instrument identity rules cover the actions"
  },
  "K5": {
   "project_objective": "Retrieval and thinking-budget choices are measured",
   "implementation_ref": "see outcome reviews; pinned at b61af8f / 1cc2043",
   "gap": "none beyond existing work",
   "operational_change": "none",
   "benefit_direction": "n/a",
   "owner": "handoffs/active/knowledge-pipelines.md",
   "execution_conditions": "n/a",
   "closure_basis": "K11 lexical sweep, K7 recall@k and TB-1/E-2 cover the actions"
  },
  "K6": {
   "project_objective": "Injection claims stay within evidence",
   "implementation_ref": "see outcome reviews; pinned at b61af8f / 1cc2043",
   "gap": "none beyond existing work",
   "operational_change": "none",
   "benefit_direction": "n/a",
   "owner": "handoffs/active/harness-program.md",
   "execution_conditions": "n/a",
   "closure_basis": "CT-20 wording rule, CT-17 path table and CM-3 typed returns cover the actions"
  },
  "K7": {
   "project_objective": "Reviewer calibration and fresh-context review exist",
   "implementation_ref": "see outcome reviews; pinned at b61af8f / 1cc2043",
   "gap": "none beyond existing work",
   "operational_change": "none",
   "benefit_direction": "n/a",
   "owner": "handoffs/active/reviewer-control-plane.md",
   "execution_conditions": "n/a",
   "closure_basis": "Reviewer-calibration-accounting and RA-13a cover the actions"
  },
  "M1": {
   "project_objective": "Cross-session coordination evidence",
   "implementation_ref": "pinned at b61af8f / 1cc2043",
   "gap": "no immediate step: the deciding input does not exist yet",
   "operational_change": "none until the trigger fires",
   "benefit_direction": "n/a",
   "owner": "handoffs/active/harness-program.md",
   "execution_conditions": "trigger: a logged cross-session incident whose cause is an unverifiable completion claim or a missing reference frame",
   "closure_basis": "Monitor; unfired trigger is dormant, not blocked"
  },
  "M2": {
   "project_objective": "Agentic eval reliability metrics",
   "implementation_ref": "pinned at b61af8f / 1cc2043",
   "gap": "no immediate step: the deciding input does not exist yet",
   "operational_change": "none until the trigger fires",
   "benefit_direction": "n/a",
   "owner": "handoffs/active/eval-tower-program.md",
   "execution_conditions": "trigger: the first agentic eval with a persisted trajectory, or the first scaffold/harness comparison, runs in the tower",
   "closure_basis": "Monitor; unfired trigger is dormant, not blocked"
  },
  "M3": {
   "project_objective": "Capability-tracking injection defense",
   "implementation_ref": "pinned at b61af8f / 1cc2043",
   "gap": "no immediate step: the deciding input does not exist yet",
   "operational_change": "none until the trigger fires",
   "benefit_direction": "n/a",
   "owner": "handoffs/active/harness-program.md",
   "execution_conditions": "trigger: a plan-first REPL mode is proposed",
   "closure_basis": "Monitor; unfired trigger is dormant, not blocked"
  },
  "M4": {
   "project_objective": "Consult and pairing design",
   "implementation_ref": "pinned at b61af8f / 1cc2043",
   "gap": "no immediate step: the deciding input does not exist yet",
   "operational_change": "none until the trigger fires",
   "benefit_direction": "n/a",
   "owner": "handoffs/active/routing-program.md",
   "execution_conditions": "trigger: a consult-larger-model routing spec is written in routing-program",
   "closure_basis": "Monitor; unfired trigger is dormant, not blocked"
  },
  "M5": {
   "project_objective": "Contextual encoding beyond breadcrumbs",
   "implementation_ref": "pinned at b61af8f / 1cc2043",
   "gap": "no immediate step: the deciding input does not exist yet",
   "operational_change": "none until the trigger fires",
   "benefit_direction": "n/a",
   "owner": "handoffs/active/knowledge-pipelines.md",
   "execution_conditions": "trigger: AEI-KB-BREADCRUMB-AB ends keep",
   "closure_basis": "Monitor; unfired trigger is dormant, not blocked"
  },
  "M6": {
   "project_objective": "Adaptive-attack robustness",
   "implementation_ref": "pinned at b61af8f / 1cc2043",
   "gap": "no immediate step: the deciding input does not exist yet",
   "operational_change": "none until the trigger fires",
   "benefit_direction": "n/a",
   "owner": "handoffs/active/harness-program.md",
   "execution_conditions": "trigger: AEI-CT18-ARMD-RUN shows arm D static ASR below arms A-C",
   "closure_basis": "Monitor; unfired trigger is dormant, not blocked"
  },
  "M7": {
   "project_objective": "Reviewer arms beyond the probe",
   "implementation_ref": "pinned at b61af8f / 1cc2043",
   "gap": "no immediate step: the deciding input does not exist yet",
   "operational_change": "none until the trigger fires",
   "benefit_direction": "n/a",
   "owner": "handoffs/active/reviewer-control-plane.md",
   "execution_conditions": "trigger: RM-3 screening tier opens, C-CRAB saturates, or a reviewer training lane with a verifiable reward exists",
   "closure_basis": "Monitor; unfired trigger is dormant, not blocked"
  },
  "M8": {
   "project_objective": "Tool description and naming evaluation",
   "implementation_ref": "pinned at b61af8f / 1cc2043",
   "gap": "no immediate step: the deciding input does not exist yet",
   "operational_change": "none until the trigger fires",
   "benefit_direction": "n/a",
   "owner": "handoffs/active/harness-program.md",
   "execution_conditions": "trigger: a change to REPL tool descriptions or the tool set is proposed",
   "closure_basis": "Monitor; unfired trigger is dormant, not blocked"
  }
 },
 "actionable_additions": [
  {
   "ledger_id": "S1-1",
   "source": "intake-2907 pp.43-44 (discovery) + grounding Q1",
   "action": "Truncated or declined generations must not be returned as complete answers",
   "terminal_mapping": "P1 / AEI-CHAT-FINISH-REASON"
  },
  {
   "ledger_id": "S1-2",
   "source": "intake-2907 pp.22-23, 75 (discovery) + grounding Q2",
   "action": "Keep the prompt prefix byte-stable for prefix/KV cache hits",
   "terminal_mapping": "K2 (covered by existing work)"
  },
  {
   "ledger_id": "S1-3",
   "source": "intake-2907 pp.39-41 + intake-2911 claim 1 + grounding Q3",
   "action": "Tool failures and truncation reach the model as instructive observations",
   "terminal_mapping": "P1 / AEI-TRUNC-NOTICE"
  },
  {
   "ledger_id": "S1-4",
   "source": "intake-2907 p.78 + intake-2909 claim 3",
   "action": "Elide old tool results in long runs",
   "terminal_mapping": "K2 (covered by existing work)"
  },
  {
   "ledger_id": "S1-5",
   "source": "intake-2914 claims 0-1",
   "action": "Do not trust a review step that has no new evidence",
   "terminal_mapping": "P3 / AEI-REV-FLIPS"
  },
  {
   "ledger_id": "S1-6",
   "source": "intake-2910, intake-2921, intake-2934",
   "action": "Eval statistics: graded fraction, rerun noise, pass^k",
   "terminal_mapping": "P2 / AEI-DROPS-MANIFEST"
  },
  {
   "ledger_id": "S1-7",
   "source": "intake-2912, intake-2924",
   "action": "kb-search document-situating context",
   "terminal_mapping": "P5 / AEI-KB-BREADCRUMB-AB"
  },
  {
   "ledger_id": "S1-8",
   "source": "intake-2907 p.139 (discovery) + grounding Q8",
   "action": "Untrusted reading and external sending in one role",
   "terminal_mapping": "P4 / AEI-HTTPPOST-GUARD"
  },
  {
   "ledger_id": "S1-9",
   "source": "intake-2908 claims 0-4",
   "action": "Goal list with verified pass status for long-running sessions",
   "terminal_mapping": "K2 (covered by existing work)"
  },
  {
   "ledger_id": "i2908-A1",
   "source": "intake-2908 claims 3-4",
   "action": "Premature-pass check in agent loop protocol",
   "terminal_mapping": "K2 (covered by existing work)"
  },
  {
   "ledger_id": "i2908-A2",
   "source": "intake-2908 claim 2",
   "action": "A/B JSON versus Markdown for model-mutated state",
   "terminal_mapping": "K2 knowledge-only"
  },
  {
   "ledger_id": "i2909-A1",
   "source": "intake-2909 claim 3",
   "action": "Tool-result-clearing arm in the compaction A/B",
   "terminal_mapping": "K2 (covered by existing work)"
  },
  {
   "ledger_id": "i2909-A2",
   "source": "intake-2909 claim 2",
   "action": "Hybrid up-front plus just-in-time retrieval for REPL agents",
   "terminal_mapping": "K2 (covered by existing work)"
  },
  {
   "ledger_id": "i2910-A1",
   "source": "intake-2910 claim 3",
   "action": "Reference-solution check and 0%-over-N task audit",
   "terminal_mapping": "K4 (covered by existing work)"
  },
  {
   "ledger_id": "i2910-A2",
   "source": "intake-2910 claim 4 + intake-2922 claim 3",
   "action": "Report pass^k beside pass@1",
   "terminal_mapping": "M2 (monitor)"
  },
  {
   "ledger_id": "i2910-A3",
   "source": "intake-2910 claims 0, 4",
   "action": "Grade outcome first; capability vs regression tags",
   "terminal_mapping": "K4 knowledge-only"
  },
  {
   "ledger_id": "i2910-A4",
   "source": "intake-2910 (graders table)",
   "action": "Calibrate LLM-judge graders on human labels",
   "terminal_mapping": "K4 (covered by existing work)"
  },
  {
   "ledger_id": "i2911-A1",
   "source": "intake-2911 claim 0",
   "action": "Tool-eval harness with held-out split",
   "terminal_mapping": "M8 (monitor)"
  },
  {
   "ledger_id": "i2911-A2",
   "source": "intake-2911 claims 1-2",
   "action": "response_format and narrowing truncation messages",
   "terminal_mapping": "P1 / AEI-TRUNC-NOTICE"
  },
  {
   "ledger_id": "i2911-A3",
   "source": "intake-2911 claim 3",
   "action": "Namespacing A/B on local models",
   "terminal_mapping": "M8 (monitor)"
  },
  {
   "ledger_id": "i2912-A1",
   "source": "intake-2912 claims 0-2",
   "action": "Contextual prefix on kb-search",
   "terminal_mapping": "P5 / AEI-KB-BREADCRUMB-AB"
  },
  {
   "ledger_id": "i2912-A2",
   "source": "intake-2912 claim 1",
   "action": "BM25 leg with rank fusion",
   "terminal_mapping": "K5 (covered by existing work)"
  },
  {
   "ledger_id": "i2912-A3",
   "source": "intake-2912 claim 4",
   "action": "Sweep chunk count k for local readers",
   "terminal_mapping": "K5 knowledge-only"
  },
  {
   "ledger_id": "i2913-A1",
   "source": "intake-2913 claims 0-1",
   "action": "Provenance tags plus policy check on one tool class",
   "terminal_mapping": "M3 (monitor)"
  },
  {
   "ledger_id": "i2913-A2",
   "source": "intake-2913 claim 3",
   "action": "Measure the token multiplier before a P/Q split",
   "terminal_mapping": "M3 (monitor)"
  },
  {
   "ledger_id": "i2913-A3",
   "source": "intake-2913 (Q-LLM cost)",
   "action": "Quarantined LLM on a small local model",
   "terminal_mapping": "M3 (monitor)"
  },
  {
   "ledger_id": "i2913-A4",
   "source": "intake-2913 claim 2",
   "action": "Never claim provable security without the interpreter",
   "terminal_mapping": "K6 (covered by existing work)"
  },
  {
   "ledger_id": "i2914-A1",
   "source": "intake-2914 claims 0-1",
   "action": "A no-evidence review step is advisory unless an A/B wins",
   "terminal_mapping": "P3 / AEI-REV-A1-LOCATE-PROBE"
  },
  {
   "ledger_id": "i2914-A2",
   "source": "intake-2914 (answer-change analysis)",
   "action": "Change matrix per review step",
   "terminal_mapping": "P3 / AEI-REV-FLIPS"
  },
  {
   "ledger_id": "i2914-A3",
   "source": "intake-2914 claim 3",
   "action": "Route escalation to evidence-bearing checks",
   "terminal_mapping": "K7 (covered by existing work)"
  },
  {
   "ledger_id": "i2914-A4",
   "source": "intake-2914 (scope)",
   "action": "One bounded probe on our reviewer before treating as fact",
   "terminal_mapping": "P3 / AEI-REV-A1-LOCATE-PROBE"
  },
  {
   "ledger_id": "i2915-A1",
   "source": "intake-2915 claims 1, 4",
   "action": "Reasoning-effort prior tested with 3+ trials",
   "terminal_mapping": "K5 (covered by existing work)"
  },
  {
   "ledger_id": "i2915-A2",
   "source": "intake-2915 claim 2",
   "action": "Cost axes per eval cell (tokens, wall-seconds)",
   "terminal_mapping": "M2 (monitor)"
  },
  {
   "ledger_id": "i2915-A3",
   "source": "intake-2915 claim 3",
   "action": "LLM-aided log inspection on agent runs",
   "terminal_mapping": "M2 (monitor)"
  },
  {
   "ledger_id": "i2915-A4",
   "source": "intake-2915 (surfaced)",
   "action": "Dive 2611.04399 and 2602.16666",
   "terminal_mapping": "K5 knowledge-only (discharged)"
  },
  {
   "ledger_id": "i2915-A5",
   "source": "intake-2915 (A3 limitations)",
   "action": "Record weights hash and quant per eval row",
   "terminal_mapping": "K4 (covered by existing work)"
  },
  {
   "ledger_id": "i2916-A1",
   "source": "intake-2916 claims 0-1",
   "action": "Single-writer delegation rule",
   "terminal_mapping": "K1 (covered by existing work)"
  },
  {
   "ledger_id": "i2916-A2",
   "source": "intake-2916 claim 2",
   "action": "Small summariser model for compaction",
   "terminal_mapping": "K2 (covered by existing work)"
  },
  {
   "ledger_id": "i2917-A1",
   "source": "intake-2917 claim 4",
   "action": "Checkable evidence on bus completion claims",
   "terminal_mapping": "M1 (monitor)"
  },
  {
   "ledger_id": "i2917-A2",
   "source": "intake-2917 (first-turn plan)",
   "action": "First-turn plan with paths on cross-session handoffs",
   "terminal_mapping": "M1 (monitor)"
  },
  {
   "ledger_id": "i2917-A3",
   "source": "intake-2917 claim 4",
   "action": "Shared record of semantic interface decisions",
   "terminal_mapping": "M1 (monitor)"
  },
  {
   "ledger_id": "i2917-A4",
   "source": "intake-2917 claims 1-2",
   "action": "Solo-first prior in fan-out rules",
   "terminal_mapping": "K1 (covered by existing work)"
  },
  {
   "ledger_id": "w1a-A1",
   "source": "intake-2918 claims 1-2",
   "action": "Clean-context reviewer with builder-side filter",
   "terminal_mapping": "K7 (covered by existing work)"
  },
  {
   "ledger_id": "w1a-A2",
   "source": "intake-2918 claim 3",
   "action": "Consult design forks full context",
   "terminal_mapping": "M4 (monitor)"
  },
  {
   "ledger_id": "w1a-A3",
   "source": "intake-2918 claim 0",
   "action": "Cross-reference the single-writer rule",
   "terminal_mapping": "K1 knowledge-only"
  },
  {
   "ledger_id": "w1e-A1",
   "source": "intake-2919 claims 2-3",
   "action": "Larger model opens worker/architect exchanges",
   "terminal_mapping": "M4 (monitor)"
  },
  {
   "ledger_id": "w1e-A2",
   "source": "intake-2919 claim 4",
   "action": "Capable session states the reference frame first",
   "terminal_mapping": "M1 (monitor)"
  },
  {
   "ledger_id": "w1e-A3",
   "source": "intake-2919 claim 0",
   "action": "Collaboration-aware eval for small collaborating models",
   "terminal_mapping": "M4 (monitor)"
  },
  {
   "ledger_id": "w1f-A1",
   "source": "intake-2920 claim 0",
   "action": "Staleness check at bus task boundaries",
   "terminal_mapping": "K1 (covered by existing work)"
  },
  {
   "ledger_id": "w1f-A2",
   "source": "intake-2920 claim 2",
   "action": "Assistance-seeking metric",
   "terminal_mapping": "M1 (monitor)"
  },
  {
   "ledger_id": "w1f-A3",
   "source": "intake-2920 claim 4",
   "action": "Stuck detection in code, not agent budgets",
   "terminal_mapping": "K1 knowledge-only"
  },
  {
   "ledger_id": "w1g-A1",
   "source": "intake-2921 claims 0-1",
   "action": "Graded-fraction column and imbalance flag",
   "terminal_mapping": "P2 / AEI-DROPS-MANIFEST"
  },
  {
   "ledger_id": "w1g-A2",
   "source": "intake-2921 claim 3",
   "action": "Provenance tag on trace actions",
   "terminal_mapping": "M2 (monitor)"
  },
  {
   "ledger_id": "w1g-A3",
   "source": "intake-2921 claim 2",
   "action": "All-span vs root-span token ratio",
   "terminal_mapping": "P2 / AEI-TOKEN-SPAN-RATIO"
  },
  {
   "ledger_id": "w1g-A4",
   "source": "intake-2921 claims 0-2",
   "action": "Treat HAL cost and Generalist numbers as suspect",
   "terminal_mapping": "K5 knowledge-only"
  },
  {
   "ledger_id": "w1h-A1",
   "source": "intake-2922 claim 3",
   "action": "Outcome and resource consistency from repeated records",
   "terminal_mapping": "K7 (covered by existing work)"
  },
  {
   "ledger_id": "w1h-A2",
   "source": "intake-2922 (predictability)",
   "action": "ECE, AUROC, Brier from stored confidence",
   "terminal_mapping": "K7 (covered by existing work)"
  },
  {
   "ledger_id": "w1h-A3",
   "source": "intake-2922 (K=5 temp 0)",
   "action": "Check byte-identical repeats before trusting consistency",
   "terminal_mapping": "K4 (covered by existing work)"
  },
  {
   "ledger_id": "w1h-A4",
   "source": "intake-2922 claim 4",
   "action": "Prompt-paraphrase robustness probe",
   "terminal_mapping": "M2 (monitor)"
  },
  {
   "ledger_id": "w1h-A5",
   "source": "intake-2922 claim 0",
   "action": "Adopt the aggregate reliability score",
   "terminal_mapping": "decline: the paper itself calls its aggregation subjective; EPYC claim grammar is per metric"
  },
  {
   "ledger_id": "w1b-A1",
   "source": "intake-2923 claim 1",
   "action": "Ablate prefix, BM25 and rerank separately",
   "terminal_mapping": "P5 / AEI-KB-BREADCRUMB-AB"
  },
  {
   "ledger_id": "w1c-A1",
   "source": "intake-2924 claim 0",
   "action": "Untrained late chunking on GTE-ModernColBERT",
   "terminal_mapping": "decline: measured -0.3 nDCG@10 on the same encoder family"
  },
  {
   "ledger_id": "w1c-A2",
   "source": "intake-2924 claims 0-2",
   "action": "Zero-LLM breadcrumb prefix A/B",
   "terminal_mapping": "P5 / AEI-KB-BREADCRUMB-AB"
  },
  {
   "ledger_id": "w1c-A3",
   "source": "intake-2924 claim 1 + intake-2912",
   "action": "LLM-written prefix if breadcrumb lifts",
   "terminal_mapping": "M5 (monitor)"
  },
  {
   "ledger_id": "w1c-A4",
   "source": "intake-2924 claim 3",
   "action": "InSeNT trained embedder",
   "terminal_mapping": "M5 (monitor)"
  },
  {
   "ledger_id": "w1d-A1",
   "source": "intake-2925",
   "action": "Record late chunking as a measured null on ColBERT",
   "terminal_mapping": "K5 knowledge-only"
  },
  {
   "ledger_id": "w1d-A2",
   "source": "intake-2925 claim 0",
   "action": "Late chunking for a future dense component",
   "terminal_mapping": "decline: no dense retriever consumer exists"
  },
  {
   "ledger_id": "w1i-A1",
   "source": "intake-2926 claim 1",
   "action": "Tiered-risk naming note",
   "terminal_mapping": "K6 knowledge-only"
  },
  {
   "ledger_id": "w1i-A2",
   "source": "intake-2926 claims 1-2",
   "action": "Prompt screening, output auditing, plan-template caching",
   "terminal_mapping": "decline: the source has no measurement"
  },
  {
   "ledger_id": "w1j-A1",
   "source": "intake-2927 claims 0-3",
   "action": "CT-18 arm D tool-output sanitizer",
   "terminal_mapping": "P4 / AEI-CT18-ARMD-RUN"
  },
  {
   "ledger_id": "w1j-A2",
   "source": "intake-2927 claim 3",
   "action": "Second-order semantic attack templates",
   "terminal_mapping": "M6 (monitor)"
  },
  {
   "ledger_id": "w1j-A3",
   "source": "intake-2927 claim 2",
   "action": "Use AgentDojo-Revised if imported",
   "terminal_mapping": "K6 knowledge-only"
  },
  {
   "ledger_id": "w1k-A1",
   "source": "intake-2928 claims 0-1",
   "action": "Boundary-laundering static check",
   "terminal_mapping": "P4 / AEI-BOUNDARY-LAUNDER-LINT"
  },
  {
   "ledger_id": "w1k-A2",
   "source": "intake-2928 claim 3",
   "action": "Fixed-plan fraction of REPL tool chains",
   "terminal_mapping": "M3 (monitor)"
  },
  {
   "ledger_id": "w1k-A3",
   "source": "intake-2928 claim 4",
   "action": "Return schemas in REPL tool descriptions",
   "terminal_mapping": "K6 (covered by existing work)"
  },
  {
   "ledger_id": "w1l-A1",
   "source": "intake-2929 claims 1, 4",
   "action": "Fair-evaluation checklist on reviewer arms",
   "terminal_mapping": "P3 / AEI-REV-FLIPS"
  },
  {
   "ledger_id": "w1l-A2",
   "source": "intake-2929 claim 1",
   "action": "A1 stays a negative control",
   "terminal_mapping": "P3 / AEI-REV-A1-LOCATE-PROBE"
  },
  {
   "ledger_id": "w1l-A3",
   "source": "intake-2929 claim 2",
   "action": "Gate feedback into a worker retry",
   "terminal_mapping": "M7 (monitor)"
  },
  {
   "ledger_id": "w1l-A4",
   "source": "intake-2929 claim 3",
   "action": "Decomposed per-claim verifier arm",
   "terminal_mapping": "M7 (monitor)"
  },
  {
   "ledger_id": "w1m-A1",
   "source": "intake-2930 claims 0-1",
   "action": "Fix and break rates per arm",
   "terminal_mapping": "P3 / AEI-REV-FLIPS"
  },
  {
   "ledger_id": "w1m-A2",
   "source": "intake-2930 claim 2",
   "action": "SFT on self-review traces",
   "terminal_mapping": "decline: the source's SFT controls gave delta at most +1.8 or negative (behaviour collapse)"
  },
  {
   "ledger_id": "w1m-A3",
   "source": "intake-2930 claims 0, 4",
   "action": "RL self-correction feasibility note",
   "terminal_mapping": "M7 (monitor)"
  },
  {
   "ledger_id": "w1m-A4",
   "source": "intake-2930 claim 3",
   "action": "Keep A1 as status-quo anchor",
   "terminal_mapping": "P3 / AEI-REV-A1-LOCATE-PROBE"
  },
  {
   "ledger_id": "w2a-A1",
   "source": "intake-2931",
   "action": "Adaptive-attack arm and cross-evaluation grid",
   "terminal_mapping": "M6 (monitor)"
  },
  {
   "ledger_id": "w2a-A2",
   "source": "intake-2931",
   "action": "Valid-output rate and utility beside ASR",
   "terminal_mapping": "P4 / AEI-CT18-ARMD-RUN"
  },
  {
   "ledger_id": "w2b-A1",
   "source": "intake-2932",
   "action": "Arm D-1 detect-and-extract guardrail",
   "terminal_mapping": "P4 / AEI-CT18-ARMD-PREP"
  },
  {
   "ledger_id": "w2b-A2",
   "source": "intake-2932",
   "action": "Injection-definition prompt ablation",
   "terminal_mapping": "P4 / AEI-CT18-ARMD-PREP"
  },
  {
   "ledger_id": "w2c-A1",
   "source": "intake-2933",
   "action": "Arm D-2 DataFilter weights via GGUF",
   "terminal_mapping": "P4 / AEI-CT18-ARMD-PREP"
  },
  {
   "ledger_id": "w2c-A2",
   "source": "intake-2933",
   "action": "Filter sees trusted task; false-removal rate",
   "terminal_mapping": "P4 / AEI-CT18-ARMD-RUN"
  },
  {
   "ledger_id": "w2f-A1",
   "source": "intake-2936",
   "action": "Structure baseline plus in-corpus and in-document metrics",
   "terminal_mapping": "P5 / AEI-KB-BREADCRUMB-AB"
  },
  {
   "ledger_id": "w2f-A2",
   "source": "intake-2936",
   "action": "LumberChunker or proposition chunking",
   "terminal_mapping": "decline: no in-corpus gain over paragraph chunking at about 1000x lower throughput (source Table 3)"
  },
  {
   "ledger_id": "w2d-A1",
   "source": "intake-2934",
   "action": "Rerun arm plus discordance-based MDE",
   "terminal_mapping": "P2 / AEI-RERUN-ARM-OD"
  },
  {
   "ledger_id": "w2d-A2",
   "source": "intake-2934",
   "action": "Decompose harness token cost",
   "terminal_mapping": "M2 (monitor)"
  },
  {
   "ledger_id": "w2e-A1",
   "source": "intake-2935",
   "action": "Drops manifest plus named reporting rule",
   "terminal_mapping": "P2 / AEI-DROPS-MANIFEST"
  },
  {
   "ledger_id": "w2e-A2",
   "source": "intake-2935",
   "action": "Re-grade reviewer rollouts under an alternative rule",
   "terminal_mapping": "M7 (monitor)"
  },
  {
   "ledger_id": "w2g-A1",
   "source": "intake-2937",
   "action": "Comprehensive-prompt arm before multi-reviewer arms",
   "terminal_mapping": "P3 / AEI-REV-A1-LOCATE-PROBE"
  },
  {
   "ledger_id": "w2g-A2",
   "source": "intake-2937",
   "action": "Known-bug reviewer corpus from repo history",
   "terminal_mapping": "M7 (monitor)"
  },
  {
   "ledger_id": "w2h-A1",
   "source": "intake-2938",
   "action": "Wait-continuation arm on A1",
   "terminal_mapping": "decline: source has no correct-trace control and A1 AUC is near chance; reopen only if the location arm lifts"
  },
  {
   "ledger_id": "w2i-A1",
   "source": "intake-2939",
   "action": "Check message role of the worker patch in the A1 runner",
   "terminal_mapping": "P3 / AEI-REV-A1-PRECHECK"
  },
  {
   "ledger_id": "w2i-A2",
   "source": "intake-2939",
   "action": "Role-relabel arm on A1",
   "terminal_mapping": "decline: flagging-only gains, needs the error location, false positives untested by the authors"
  },
  {
   "ledger_id": "w2j-A1",
   "source": "intake-2940",
   "action": "Oracle defect-location arm on A1",
   "terminal_mapping": "P3 / AEI-REV-A1-LOCATE-PROBE"
  },
  {
   "ledger_id": "w2k-A1",
   "source": "intake-2941",
   "action": "RISE-style self-correction fine-tuning",
   "terminal_mapping": "M7 (monitor)"
  }
 ],
 "steering_reconciliation": [
  {
   "seq": 1,
   "stage": 1,
   "ts": "2026-11-24T10:30:00Z",
   "verbatim": "Operator authorization: accept ALL recommended deep dives and literature expansions, for up to THREE Stage 2 sweeps. Do not ask the operator about those. Stop after producing the Stage 3 plan. Do NOT apply handoff or index changes; plan approval is the operator's call.",
   "disposition": "context-only",
   "plan_ref": null,
   "reason": "Process authorisation: governed the three sweeps (sweep 1 reference dives, waves 1 and 2) and the stop at Stage 3; it creates no plan item"
  }
 ],
 "opportunity_scan": [
  {
   "scan_id": "S01",
   "source_ref": "intake-2922 claim 0; intake-2924 claim 0; intake-2925 claim 0; intake-2926 claims 1-2; intake-2930 claim 2; intake-2936; intake-2938; intake-2939",
   "implementation_ref": "pinned at b61af8f / 1cc2043",
   "mechanism": "declined mechanisms",
   "consumer": "none",
   "application": "none",
   "disposition": "declined",
   "ledger_ids": [
    "w1h-A5",
    "w1c-A1",
    "w1d-A2",
    "w1i-A2",
    "w1m-A2",
    "w2f-A2",
    "w2h-A1",
    "w2i-A2"
   ],
   "basis": "explicit declines with per-row reasons"
  },
  {
   "scan_id": "S02",
   "source_ref": "intake-2916 claims 0-1; intake-2917 claims 1-2; intake-2918 claim 0; intake-2920 claim 0; intake-2920 claim 4",
   "implementation_ref": "see outcome reviews; pinned at b61af8f / 1cc2043",
   "mechanism": "Parallel sessions coordinate without conflicting writes",
   "consumer": "handoffs/active/harness-program.md",
   "application": "none",
   "disposition": "covered",
   "ledger_ids": [
    "i2916-A1",
    "i2917-A4",
    "w1a-A3",
    "w1f-A1",
    "w1f-A3"
   ],
   "basis": "Single writer, per-session worktrees, bus drain and done_when checks already implement the sources' remedies"
  },
  {
   "scan_id": "S03",
   "source_ref": "intake-2907 p.78 + intake-2909 claim 3; intake-2907 pp.22-23, 75 (discovery) + grounding Q2; intake-2908 claim 2; intake-2908 claims 0-4; intake-2908 claims 3-4; intake-2909 claim 2; intake-2909 claim 3; intake-2916 claim 2",
   "implementation_ref": "see outcome reviews; pinned at b61af8f / 1cc2043",
   "mechanism": "Long runs keep verified progress and a bounded context",
   "consumer": "handoffs/active/context-and-token-economy.md",
   "application": "none",
   "disposition": "covered",
   "ledger_ids": [
    "S1-2",
    "S1-4",
    "S1-9",
    "i2908-A1",
    "i2908-A2",
    "i2909-A1",
    "i2909-A2",
    "i2916-A2"
   ],
   "basis": "Existing boxes (PREFIX-CACHE-LAYOUT-AB, CF-AKV-0, TOC-CMP-4, CF-AM-1, REPL-EMB-CONSUMER-GATE) and done_when checks cover the actions"
  },
  {
   "scan_id": "S04",
   "source_ref": "intake-2910 (graders table); intake-2910 claim 3; intake-2910 claims 0, 4; intake-2915 (A3 limitations); intake-2922 (K=5 temp 0)",
   "implementation_ref": "see outcome reviews; pinned at b61af8f / 1cc2043",
   "mechanism": "Eval tasks and graders are valid",
   "consumer": "handoffs/active/eval-tower-program.md",
   "application": "none",
   "disposition": "covered",
   "ledger_ids": [
    "i2910-A1",
    "i2910-A3",
    "i2910-A4",
    "i2915-A5",
    "w1h-A3"
   ],
   "basis": "EV-19 gold self-check, oracle builders and instrument identity rules cover the actions"
  },
  {
   "scan_id": "S05",
   "source_ref": "intake-2912 claim 1; intake-2912 claim 4; intake-2915 (surfaced); intake-2915 claims 1, 4; intake-2921 claims 0-2; intake-2925",
   "implementation_ref": "see outcome reviews; pinned at b61af8f / 1cc2043",
   "mechanism": "Retrieval and thinking-budget choices are measured",
   "consumer": "handoffs/active/knowledge-pipelines.md",
   "application": "none",
   "disposition": "covered",
   "ledger_ids": [
    "i2912-A2",
    "i2912-A3",
    "i2915-A1",
    "i2915-A4",
    "w1g-A4",
    "w1d-A1"
   ],
   "basis": "K11 lexical sweep, K7 recall@k and TB-1/E-2 cover the actions"
  },
  {
   "scan_id": "S06",
   "source_ref": "intake-2913 claim 2; intake-2926 claim 1; intake-2927 claim 2; intake-2928 claim 4",
   "implementation_ref": "see outcome reviews; pinned at b61af8f / 1cc2043",
   "mechanism": "Injection claims stay within evidence",
   "consumer": "handoffs/active/harness-program.md",
   "application": "none",
   "disposition": "covered",
   "ledger_ids": [
    "i2913-A4",
    "w1i-A1",
    "w1j-A3",
    "w1k-A3"
   ],
   "basis": "CT-20 wording rule, CT-17 path table and CM-3 typed returns cover the actions"
  },
  {
   "scan_id": "S07",
   "source_ref": "intake-2914 claim 3; intake-2918 claims 1-2; intake-2922 (predictability); intake-2922 claim 3",
   "implementation_ref": "see outcome reviews; pinned at b61af8f / 1cc2043",
   "mechanism": "Reviewer calibration and fresh-context review exist",
   "consumer": "handoffs/active/reviewer-control-plane.md",
   "application": "none",
   "disposition": "covered",
   "ledger_ids": [
    "i2914-A3",
    "w1a-A1",
    "w1h-A1",
    "w1h-A2"
   ],
   "basis": "Reviewer-calibration-accounting and RA-13a cover the actions"
  },
  {
   "scan_id": "S08",
   "source_ref": "intake-2917 (first-turn plan); intake-2917 claim 4; intake-2919 claim 4; intake-2920 claim 2",
   "implementation_ref": "pinned at b61af8f / 1cc2043",
   "mechanism": "Cross-session coordination evidence",
   "consumer": "handoffs/active/harness-program.md",
   "application": "none until the trigger fires",
   "disposition": "context-only",
   "ledger_ids": [
    "i2917-A1",
    "i2917-A2",
    "i2917-A3",
    "w1e-A2",
    "w1f-A2"
   ],
   "basis": "Monitor; unfired trigger is dormant, not blocked"
  },
  {
   "scan_id": "S09",
   "source_ref": "intake-2910 claim 4 + intake-2922 claim 3; intake-2915 claim 2; intake-2915 claim 3; intake-2921 claim 3; intake-2922 claim 4; intake-2934",
   "implementation_ref": "pinned at b61af8f / 1cc2043",
   "mechanism": "Agentic eval reliability metrics",
   "consumer": "handoffs/active/eval-tower-program.md",
   "application": "none until the trigger fires",
   "disposition": "context-only",
   "ledger_ids": [
    "i2910-A2",
    "i2915-A2",
    "i2915-A3",
    "w1g-A2",
    "w1h-A4",
    "w2d-A2"
   ],
   "basis": "Monitor; unfired trigger is dormant, not blocked"
  },
  {
   "scan_id": "S10",
   "source_ref": "intake-2913 (Q-LLM cost); intake-2913 claim 3; intake-2913 claims 0-1; intake-2928 claim 3",
   "implementation_ref": "pinned at b61af8f / 1cc2043",
   "mechanism": "Capability-tracking injection defense",
   "consumer": "handoffs/active/harness-program.md",
   "application": "none until the trigger fires",
   "disposition": "context-only",
   "ledger_ids": [
    "i2913-A1",
    "i2913-A2",
    "i2913-A3",
    "w1k-A2"
   ],
   "basis": "Monitor; unfired trigger is dormant, not blocked"
  },
  {
   "scan_id": "S11",
   "source_ref": "intake-2918 claim 3; intake-2919 claim 0; intake-2919 claims 2-3",
   "implementation_ref": "pinned at b61af8f / 1cc2043",
   "mechanism": "Consult and pairing design",
   "consumer": "handoffs/active/routing-program.md",
   "application": "none until the trigger fires",
   "disposition": "context-only",
   "ledger_ids": [
    "w1a-A2",
    "w1e-A1",
    "w1e-A3"
   ],
   "basis": "Monitor; unfired trigger is dormant, not blocked"
  },
  {
   "scan_id": "S12",
   "source_ref": "intake-2924 claim 1 + intake-2912; intake-2924 claim 3",
   "implementation_ref": "pinned at b61af8f / 1cc2043",
   "mechanism": "Contextual encoding beyond breadcrumbs",
   "consumer": "handoffs/active/knowledge-pipelines.md",
   "application": "none until the trigger fires",
   "disposition": "context-only",
   "ledger_ids": [
    "w1c-A3",
    "w1c-A4"
   ],
   "basis": "Monitor; unfired trigger is dormant, not blocked"
  },
  {
   "scan_id": "S13",
   "source_ref": "intake-2927 claim 3; intake-2931",
   "implementation_ref": "pinned at b61af8f / 1cc2043",
   "mechanism": "Adaptive-attack robustness",
   "consumer": "handoffs/active/harness-program.md",
   "application": "none until the trigger fires",
   "disposition": "context-only",
   "ledger_ids": [
    "w1j-A2",
    "w2a-A1"
   ],
   "basis": "Monitor; unfired trigger is dormant, not blocked"
  },
  {
   "scan_id": "S14",
   "source_ref": "intake-2929 claim 2; intake-2929 claim 3; intake-2930 claims 0, 4; intake-2935; intake-2937; intake-2941",
   "implementation_ref": "pinned at b61af8f / 1cc2043",
   "mechanism": "Reviewer arms beyond the probe",
   "consumer": "handoffs/active/reviewer-control-plane.md",
   "application": "none until the trigger fires",
   "disposition": "context-only",
   "ledger_ids": [
    "w1l-A3",
    "w1l-A4",
    "w1m-A3",
    "w2e-A2",
    "w2g-A2",
    "w2k-A1"
   ],
   "basis": "Monitor; unfired trigger is dormant, not blocked"
  },
  {
   "scan_id": "S15",
   "source_ref": "intake-2911 claim 0; intake-2911 claim 3",
   "implementation_ref": "pinned at b61af8f / 1cc2043",
   "mechanism": "Tool description and naming evaluation",
   "consumer": "handoffs/active/harness-program.md",
   "application": "none until the trigger fires",
   "disposition": "context-only",
   "ledger_ids": [
    "i2911-A1",
    "i2911-A3"
   ],
   "basis": "Monitor; unfired trigger is dormant, not blocked"
  },
  {
   "scan_id": "S16",
   "source_ref": "intake-2907 pp.39-41 + intake-2911 claim 1 + grounding Q3; intake-2907 pp.43-44 (discovery) + grounding Q1; intake-2911 claims 1-2",
   "implementation_ref": "epyc-orchestrator @ 1cc2043: src/backends/llama_server.py:596-612, 1102-1111 (completion_reason); src/api/models/responses.py (no finish_reason); src/llm_primitives/primitives.py:1267, 1409, 1529 (markers without hints); src/repl_environment/environment.py:1008-1085 (spill footer)",
   "mechanism": "Agent and chat answers are never silently truncated, and every truncation tells the model how to recover",
   "consumer": "handoffs/active/harness-program.md",
   "application": "Surface finish_reason/truncated on /chat; add narrowing hints to the three markers",
   "disposition": "actionable",
   "ledger_ids": [
    "S1-1",
    "S1-3",
    "i2911-A2"
   ],
   "basis": "/chat returns a length-cut answer as final; three truncation markers give no narrowing hint"
  },
  {
   "scan_id": "S17",
   "source_ref": "intake-2910, intake-2921, intake-2934; intake-2921 claim 2; intake-2921 claims 0-1; intake-2934; intake-2935",
   "implementation_ref": "EV-18 ITT fields (epyc-orchestrator ea8c7338, 3d8830ee; eval-tower-program EV-18); MEASUREMENT.md:170-184; measurement/protocols/quality-eval.md P-AB-1/P-PAIRED @ b61af8f",
   "mechanism": "Eval deltas cannot be reordered by instrument errors (ungraded rows, double-counted tokens, single-run noise)",
   "consumer": "handoffs/active/eval-tower-program.md",
   "application": "Drops manifest + graded-fraction flag; token span ratio check; operator decision on a rerun arm",
   "disposition": "actionable",
   "ledger_ids": [
    "S1-6",
    "w1g-A1",
    "w1g-A3",
    "w2d-A1",
    "w2e-A1"
   ],
   "basis": "No graded-fraction imbalance gate, no drops manifest, no proof that token accounting is single-counted, no rerun-flip control"
  },
  {
   "scan_id": "S18",
   "source_ref": "intake-2914 (answer-change analysis); intake-2914 (scope); intake-2914 claims 0-1; intake-2929 claim 1; intake-2929 claims 1, 4; intake-2930 claim 3; intake-2930 claims 0-1; intake-2937; intake-2939; intake-2940",
   "implementation_ref": "reviewer-control-plane.md RM-2 @ b61af8f (A1 FA 45.8%, FR 41.7%, AUC 0.463, 48 rows); epyc-orchestrator scripts/analysis/reviewer_calibration_report.py:304-345 @ 1cc2043",
   "mechanism": "Reviewer arm decisions rest on fair, flip-aware comparisons, and A1 is either justified or closed",
   "consumer": "handoffs/active/reviewer-control-plane.md",
   "application": "Offline flip report; zero-inference precheck; one bounded two-arm probe with a closure rule",
   "disposition": "actionable",
   "ledger_ids": [
    "S1-5",
    "i2914-A1",
    "i2914-A2",
    "i2914-A4",
    "w1l-A1",
    "w1l-A2",
    "w1m-A1",
    "w1m-A4",
    "w2g-A1",
    "w2i-A1",
    "w2j-A1"
   ],
   "basis": "No fix/break counts or fairness line; no located or comprehensive-prompt arm; A1 still consumes arm budget"
  },
  {
   "scan_id": "S19",
   "source_ref": "intake-2907 p.139 (discovery) + grounding Q8; intake-2927 claims 0-3; intake-2928 claims 0-1; intake-2931; intake-2932; intake-2933",
   "implementation_ref": "harness-program CT-18/CT-20/CT-21 @ b61af8f (IB2 fixtures, baseline worker ASR about 45.8%); epyc-orchestrator orchestration/tools/web.py:51-81, src/repl_environment/web_guard.py @ 1cc2043",
   "mechanism": "Injected tool output cannot steer agents into external effects; measured defenses beyond prompt wording",
   "consumer": "handoffs/active/harness-program.md",
   "application": "Arm D prep and run; boundary-laundering lint; http_post destination guard",
   "disposition": "actionable",
   "ledger_ids": [
    "S1-8",
    "w1j-A1",
    "w1k-A1",
    "w2a-A2",
    "w2b-A1",
    "w2b-A2",
    "w2c-A1",
    "w2c-A2"
   ],
   "basis": "No tool-output sanitizer arm; no check for untrusted data in delegated instructions; http_post unguarded"
  },
  {
   "scan_id": "S20",
   "source_ref": "intake-2912 claims 0-2; intake-2912, intake-2924; intake-2923 claim 1; intake-2924 claims 0-2; intake-2936",
   "implementation_ref": "epyc-orchestrator src/retrieval/kb_rag.py:663, 808, 917-1062; src/retrieval/markdown_chunker.py:93-170; scripts/kb_rag/eval_k7.py @ 1cc2043; knowledge-pipelines status (K7, K11)",
   "mechanism": "kb-search finds the right file and passage for prior-decision lookups",
   "consumer": "handoffs/active/knowledge-pipelines.md",
   "application": "Side index with breadcrumb-prefixed encoding, measured on K7 and an in-document subset",
   "disposition": "actionable",
   "ledger_ids": [
    "S1-7",
    "i2912-A1",
    "w1b-A1",
    "w1c-A2",
    "w2f-A1"
   ],
   "basis": "Encoded chunk text carries no file path or breadcrumb; paragraph sub-chunks lose their heading"
  }
 ],
 "outcome_reviews": {
  "S1-1": {
   "required_outcome": "A length-cut /chat answer reaches the client marked truncated",
   "review_status": "preserved",
   "review_basis": "Grounding: /chat response model has no finish_reason; backend already knows completion_reason",
   "task_refs": [
    {
     "owner": "handoffs/active/harness-program.md",
     "task_id": "AEI-CHAT-FINISH-REASON",
     "task_text": "- [ ] **AEI-CHAT-FINISH-REASON** [non-inference] Carry the backend completion_reason into the /chat response as finish_reason plus a truncated flag, so a length-cut answer is returned marked truncated instead of as a complete final answer (intake-2907 discovery; gap at src/api/models/responses.py @ 1cc2043, no finish_reason field).",
     "acceptance": "cd /mnt/raid0/llm/epyc-orchestrator && python -m pytest tests/unit/test_chat_finish_reason.py -q passes, covering stop, length and context_limit"
    }
   ]
  },
  "S1-2": {
   "required_outcome": "Stable-prefix layout measured before default-on",
   "review_status": "closed-with-basis",
   "review_basis": "Covered: PREFIX-CACHE-LAYOUT landed default-off and PREFIX-CACHE-LAYOUT-AB (harness-program) measures hit rate and wall time before default-on",
   "task_refs": []
  },
  "S1-3": {
   "required_outcome": "Every truncation marker tells the model how to get the rest",
   "review_status": "preserved",
   "review_basis": "Grounding: three primitives.py markers lack a narrowing hint; REPL spill already has one",
   "task_refs": [
    {
     "owner": "handoffs/active/harness-program.md",
     "task_id": "AEI-TRUNC-NOTICE",
     "task_text": "- [ ] **AEI-TRUNC-NOTICE** [non-inference] Make the three '[... truncated at N chars]' markers in src/llm_primitives/primitives.py say how to get the rest (the spilled file path with peek/grep, or a narrower request), matching the REPL spill footer (intake-2911 claim 1).",
     "acceptance": "cd /mnt/raid0/llm/epyc-orchestrator && python -m pytest tests/unit/test_truncation_notice.py -q passes and grep -c 'truncated at' src/llm_primitives/primitives.py shows every marker carries a narrowing hint"
    }
   ]
  },
  "S1-4": {
   "required_outcome": "Old tool-result elision is measured in the compaction A/B",
   "review_status": "closed-with-basis",
   "review_basis": "Covered: CF-AKV-0 (zero-inference screen of context held by old tool results), UTM-B2-RECOVERY-POINTERS and TOC-CMP-4 in context-and-token-economy",
   "task_refs": []
  },
  "S1-5": {
   "required_outcome": "Reviewer arms report fix and break counts and fairness of comparison",
   "review_status": "preserved",
   "review_basis": "A1 live AUC 0.463; no fix/break reporting today",
   "task_refs": [
    {
     "owner": "handoffs/active/reviewer-control-plane.md",
     "task_id": "AEI-REV-FLIPS",
     "task_text": "- [ ] **AEI-REV-FLIPS** [non-inference] Add per-arm fix and break counts (worker-wrong to reviewer-reject, worker-right to reviewer-reject) and a Kamoi-style fairness line (initial-prompt strength, no oracle stop, matched-token baseline present or absent) to the RM-2 arm report, computed offline from decisions already in the review ledger (intake-2930 claims 1-2, intake-2929 claim 4).",
     "acceptance": "cd /mnt/raid0/llm/epyc-orchestrator && python -m pytest tests/unit/test_reviewer_calibration_flips.py -q passes and the RM-2 report for the A1 48-row slice prints the new columns"
    }
   ]
  },
  "S1-6": {
   "required_outcome": "Eval deltas carry a drops manifest and graded-fraction imbalance flag",
   "review_status": "preserved",
   "review_basis": "EV-18 has ITT fields but no imbalance gate or drops manifest",
   "task_refs": [
    {
     "owner": "handoffs/active/eval-tower-program.md",
     "task_id": "AEI-DROPS-MANIFEST",
     "task_text": "- [ ] **AEI-DROPS-MANIFEST** [non-inference] Emit a drops manifest (n scheduled, n scored, n dropped by reason) and graded_fraction = n_scored / n_attempted per arm with every eval-tower aggregate beside EV-18's ITT fields, and flag a quality delta whose two arms' graded fractions differ by more than 5 points (intake-2921 claims 0-1, intake-2935).",
     "acceptance": "cd /mnt/raid0/llm/epyc-orchestrator && python -m pytest tests/unit/test_eval_tower_drops_manifest.py -q passes, including a fixture where unequal graded fractions raise the flag"
    }
   ]
  },
  "S1-7": {
   "required_outcome": "A measured keep/drop decision on breadcrumb-prefixed encoding",
   "review_status": "preserved",
   "review_basis": "Grounding: breadcrumb is metadata only; not encoded",
   "task_refs": [
    {
     "owner": "handoffs/active/knowledge-pipelines.md",
     "task_id": "AEI-KB-BREADCRUMB-AB",
     "task_text": "- [ ] **AEI-KB-BREADCRUMB-AB** [inference] Build a side kb-search index whose encoded chunk text is prefixed with the file path and full heading breadcrumb, and compare it with the production index on the K7 70-case pool (recall@10) plus an in-document subset, with the production index unchanged (intake-2924 claims 0-2, intake-2936, intake-2912).",
     "acceptance": "verdict tick records recall@3/5/10 for both indexes on the K7 pool and the in-document subset with the keep/drop decision under the stop rule"
    }
   ]
  },
  "S1-8": {
   "required_outcome": "http_post refuses private and metadata destinations",
   "review_status": "preserved",
   "review_basis": "Grounding: http_post has no web_guard; role permissions fix is the open TOOLPERM-DENY-DEFAULT",
   "task_refs": [
    {
     "owner": "handoffs/active/harness-program.md",
     "task_id": "AEI-HTTPPOST-GUARD",
     "task_text": "- [ ] **AEI-HTTPPOST-GUARD** [non-inference] Apply the SEC-EXEC-3 web_guard destination check to http_post (orchestration/tools/web.py), which today posts to any URL while roles holding the web category also read untrusted pages (intake-2907 discovery; intake-2928 context).",
     "acceptance": "cd /mnt/raid0/llm/epyc-orchestrator && python -m pytest tests/unit/test_web_guard_http_post.py -q passes, refusing private and metadata destinations for http_post"
    }
   ]
  },
  "S1-9": {
   "required_outcome": "Long-running loops keep verified progress and a startup check",
   "review_status": "closed-with-basis",
   "review_basis": "Covered: handoff boxes carry done_when checks (scripts/handoffs/done_when.py); autopilot startup authority gate and in-flight trial recovery (scripts/autopilot/autopilot.py:6135-6210, 7339-7352)",
   "task_refs": []
  },
  "i2908-A1": {
   "required_outcome": "No item marked done without a verifier",
   "review_status": "closed-with-basis",
   "review_basis": "Covered by done_when evidence checks on boxes; autopilot is under holds",
   "task_refs": []
  },
  "i2908-A2": {
   "required_outcome": "Model-mutated state is not corrupted by edits",
   "review_status": "closed-with-basis",
   "review_basis": "Knowledge-only: model-mutated task state goes through handoff_box.py, which never lets a model rewrite a published first line; no corruption incident to test against",
   "task_refs": []
  },
  "i2909-A1": {
   "required_outcome": "Tool-result clearing is one measured compaction arm",
   "review_status": "closed-with-basis",
   "review_basis": "Covered by CF-AKV-0 and the TOC-CMP-4 reproducible A/B",
   "task_refs": []
  },
  "i2909-A2": {
   "required_outcome": "REPL retrieval policy is decided by measurement",
   "review_status": "closed-with-basis",
   "review_basis": "Covered by the repl-embedding-retrieval track and REPL-EMB-CONSUMER-GATE (harness-program)",
   "task_refs": []
  },
  "i2910-A1": {
   "required_outcome": "Broken tasks or graders are caught before compute is spent",
   "review_status": "closed-with-basis",
   "review_basis": "Covered by EV-19 gold self-check per suite and the debugbench/livecodebench oracle builders; the tower runs single trials per item so a 0%-over-N rule has no input",
   "task_refs": []
  },
  "i2910-A2": {
   "required_outcome": "Pass^k reported when a decision turns on per-item reliability",
   "review_status": "closed-with-basis",
   "review_basis": "Existing eval-tower MONITOR on Pass^k (trigger: an agentic eval with a persisted trajectory runs in the tower); reuse _consistency_and_passk",
   "task_refs": []
  },
  "i2910-A3": {
   "required_outcome": "Graders judge outcomes",
   "review_status": "closed-with-basis",
   "review_basis": "Knowledge-only: tower scorers already grade outputs, not paths; no suite mixes the two roles today",
   "task_refs": []
  },
  "i2910-A4": {
   "required_outcome": "Judges are calibrated before use",
   "review_status": "closed-with-basis",
   "review_basis": "Covered by reviewer-calibration-accounting (P-REV-1 FA/FR/AUC/ECE)",
   "task_refs": []
  },
  "i2911-A1": {
   "required_outcome": "Tool description changes are evaluated",
   "review_status": "closed-with-basis",
   "review_basis": "Monitor: trigger is a proposed change to REPL tool descriptions or tool set",
   "task_refs": []
  },
  "i2911-A2": {
   "required_outcome": "Truncation messages name how to narrow",
   "review_status": "preserved",
   "review_basis": "The truncation half is P1; response_format waits on M8",
   "task_refs": [
    {
     "owner": "handoffs/active/harness-program.md",
     "task_id": "AEI-TRUNC-NOTICE",
     "task_text": "- [ ] **AEI-TRUNC-NOTICE** [non-inference] Make the three '[... truncated at N chars]' markers in src/llm_primitives/primitives.py say how to get the rest (the spilled file path with peek/grep, or a narrower request), matching the REPL spill footer (intake-2911 claim 1).",
     "acceptance": "cd /mnt/raid0/llm/epyc-orchestrator && python -m pytest tests/unit/test_truncation_notice.py -q passes and grep -c 'truncated at' src/llm_primitives/primitives.py shows every marker carries a narrowing hint"
    }
   ]
  },
  "i2911-A3": {
   "required_outcome": "Tool naming chosen by evaluation",
   "review_status": "closed-with-basis",
   "review_basis": "Monitor under M8: no tool-selection error class observed yet",
   "task_refs": []
  },
  "i2912-A1": {
   "required_outcome": "Contextual encoding decided by recall on our own pool",
   "review_status": "preserved",
   "review_basis": "Zero-LLM breadcrumb first; LLM prefix only on its trigger",
   "task_refs": [
    {
     "owner": "handoffs/active/knowledge-pipelines.md",
     "task_id": "AEI-KB-BREADCRUMB-AB",
     "task_text": "- [ ] **AEI-KB-BREADCRUMB-AB** [inference] Build a side kb-search index whose encoded chunk text is prefixed with the file path and full heading breadcrumb, and compare it with the production index on the K7 70-case pool (recall@10) plus an in-document subset, with the production index unchanged (intake-2924 claims 0-2, intake-2936, intake-2912).",
     "acceptance": "verdict tick records recall@3/5/10 for both indexes on the K7 pool and the in-document subset with the keep/drop decision under the stop rule"
    }
   ]
  },
  "i2912-A2": {
   "required_outcome": "Lexical signal tested on kb-search",
   "review_status": "closed-with-basis",
   "review_basis": "Covered: K11 FTS5 lexical leg exists; 2026-07-21 sweep found no recall uplift at weights 0.1-0.3 (knowledge-pipelines status)",
   "task_refs": []
  },
  "i2912-A3": {
   "required_outcome": "Retrieved-chunk count fits the reader",
   "review_status": "closed-with-basis",
   "review_basis": "Knowledge-only: K7 already reports recall@3/5/10; no reader-side k decision is pending",
   "task_refs": []
  },
  "i2913-A1": {
   "required_outcome": "Capability tracking considered when plan-first mode is proposed",
   "review_status": "closed-with-basis",
   "review_basis": "Monitor: trigger is a proposed plan-first REPL mode; intake-2928 measured 21.6 utility points lost per agent",
   "task_refs": []
  },
  "i2913-A2": {
   "required_outcome": "Overhead measured before adoption",
   "review_status": "closed-with-basis",
   "review_basis": "Monitor under M3",
   "task_refs": []
  },
  "i2913-A3": {
   "required_outcome": "Placement decided by measurement",
   "review_status": "closed-with-basis",
   "review_basis": "Monitor under M3",
   "task_refs": []
  },
  "i2913-A4": {
   "required_outcome": "Injection claims are worded by evidence class",
   "review_status": "closed-with-basis",
   "review_basis": "Covered by CT-20 wording rule (harness-program)",
   "task_refs": []
  },
  "i2914-A1": {
   "required_outcome": "A1 is closed as a negative control unless a located arm lifts",
   "review_status": "preserved",
   "review_basis": "Probe closure rule encodes it",
   "task_refs": [
    {
     "owner": "handoffs/active/reviewer-control-plane.md",
     "task_id": "AEI-REV-A1-LOCATE-PROBE",
     "task_text": "- [ ] **AEI-REV-A1-LOCATE-PROBE** [inference] Run one bounded diagnostic on the 48-row A1 slice with the incumbent A1 reviewer: arm L gives the gold defect location, arm P uses a comprehensive single-pass review prompt; report FA, FR and AUC per arm against the A1 baseline, then close A1 as a negative control unless arm L lifts (intake-2940 claims, intake-2937).",
     "acceptance": "verdict tick records FA/FR/AUC for arms L and P on the 48 rows with the pass/close decision under the stop rule"
    }
   ]
  },
  "i2914-A2": {
   "required_outcome": "Fix and break counts visible",
   "review_status": "preserved",
   "review_basis": "Offline from ledger",
   "task_refs": [
    {
     "owner": "handoffs/active/reviewer-control-plane.md",
     "task_id": "AEI-REV-FLIPS",
     "task_text": "- [ ] **AEI-REV-FLIPS** [non-inference] Add per-arm fix and break counts (worker-wrong to reviewer-reject, worker-right to reviewer-reject) and a Kamoi-style fairness line (initial-prompt strength, no oracle stop, matched-token baseline present or absent) to the RM-2 arm report, computed offline from decisions already in the review ledger (intake-2930 claims 1-2, intake-2929 claim 4).",
     "acceptance": "cd /mnt/raid0/llm/epyc-orchestrator && python -m pytest tests/unit/test_reviewer_calibration_flips.py -q passes and the RM-2 report for the A1 48-row slice prints the new columns"
    }
   ]
  },
  "i2914-A3": {
   "required_outcome": "Reviewer has an objective-verifier arm",
   "review_status": "closed-with-basis",
   "review_basis": "Covered by RM-2 arm A0 gates-only",
   "task_refs": []
  },
  "i2914-A4": {
   "required_outcome": "Bounded probe with stop rules",
   "review_status": "preserved",
   "review_basis": "Task purpose matches the outcome; P3 / AEI-REV-A1-LOCATE-PROBE",
   "task_refs": [
    {
     "owner": "handoffs/active/reviewer-control-plane.md",
     "task_id": "AEI-REV-A1-LOCATE-PROBE",
     "task_text": "- [ ] **AEI-REV-A1-LOCATE-PROBE** [inference] Run one bounded diagnostic on the 48-row A1 slice with the incumbent A1 reviewer: arm L gives the gold defect location, arm P uses a comprehensive single-pass review prompt; report FA, FR and AUC per arm against the A1 baseline, then close A1 as a negative control unless arm L lifts (intake-2940 claims, intake-2937).",
     "acceptance": "verdict tick records FA/FR/AUC for arms L and P on the 48 rows with the pass/close decision under the stop rule"
    }
   ]
  },
  "i2915-A1": {
   "required_outcome": "Thinking budget decided per model by measurement",
   "review_status": "closed-with-basis",
   "review_basis": "Covered by TB-1 per-model budget curve and E-2 effort-level curve (context-and-token-economy)",
   "task_refs": []
  },
  "i2915-A2": {
   "required_outcome": "Cost reported beside accuracy in scaffold comparisons",
   "review_status": "closed-with-basis",
   "review_basis": "Monitor: trigger is the first scaffold or harness comparison in the tower",
   "task_refs": []
  },
  "i2915-A3": {
   "required_outcome": "Shortcut behaviour found in logs",
   "review_status": "closed-with-basis",
   "review_basis": "Monitor under M2",
   "task_refs": []
  },
  "i2915-A4": {
   "required_outcome": "Sources dived",
   "review_status": "closed-with-basis",
   "review_basis": "Discharged in Stage-2b wave 1 as intake-2921 and intake-2922",
   "task_refs": []
  },
  "i2915-A5": {
   "required_outcome": "Instrument identity is recorded",
   "review_status": "closed-with-basis",
   "review_basis": "Covered by MEASUREMENT.md instrument identity and eras; stale-binary rule in CLAUDE.md",
   "task_refs": []
  },
  "i2916-A1": {
   "required_outcome": "One writer per artifact",
   "review_status": "closed-with-basis",
   "review_basis": "Covered by agents/shared/INVARIANTS.md single writer and the fan-out exceptions in OPERATING_CONSTRAINTS",
   "task_refs": []
  },
  "i2916-A2": {
   "required_outcome": "Small-model compaction measured",
   "review_status": "closed-with-basis",
   "review_basis": "Covered by CF-AM-1 (small-model gist extraction vs current folding)",
   "task_refs": []
  },
  "i2917-A1": {
   "required_outcome": "Completion claims are verifiable",
   "review_status": "closed-with-basis",
   "review_basis": "Monitor: trigger is a logged cross-session incident whose cause is an unverifiable completion claim; done_when checks already gate ticks",
   "task_refs": []
  },
  "i2917-A2": {
   "required_outcome": "Handoffs carry an explicit plan",
   "review_status": "closed-with-basis",
   "review_basis": "Monitor under M1",
   "task_refs": []
  },
  "i2917-A3": {
   "required_outcome": "Semantic decisions recorded once",
   "review_status": "closed-with-basis",
   "review_basis": "Monitor under M1",
   "task_refs": []
  },
  "i2917-A4": {
   "required_outcome": "Coupled work stays with one agent",
   "review_status": "closed-with-basis",
   "review_basis": "Covered by the ratified When NOT to fan out exceptions (tightly coupled components, shared state)",
   "task_refs": []
  },
  "w1a-A1": {
   "required_outcome": "Reviewer context is fresh",
   "review_status": "closed-with-basis",
   "review_basis": "Covered by RA-13a blind read-back pilot with fresh context per revision (reviewer-control-plane)",
   "task_refs": []
  },
  "w1a-A2": {
   "required_outcome": "Consult design decided by measurement",
   "review_status": "closed-with-basis",
   "review_basis": "Monitor: trigger is a consult-larger-model routing spec in routing-program",
   "task_refs": []
  },
  "w1a-A3": {
   "required_outcome": "Rule already stated",
   "review_status": "closed-with-basis",
   "review_basis": "Knowledge-only: INVARIANTS.md already states it",
   "task_refs": []
  },
  "w1e-A1": {
   "required_outcome": "Ordering chosen by A/B",
   "review_status": "closed-with-basis",
   "review_basis": "Monitor under M4",
   "task_refs": []
  },
  "w1e-A2": {
   "required_outcome": "Handoffs carry the shared reference frame",
   "review_status": "closed-with-basis",
   "review_basis": "Monitor under M1; bus messages already carry corr_id and paths",
   "task_refs": []
  },
  "w1e-A3": {
   "required_outcome": "Collaboration measured before relying on it",
   "review_status": "closed-with-basis",
   "review_basis": "Monitor under M4",
   "task_refs": []
  },
  "w1f-A1": {
   "required_outcome": "Sessions re-check state at boundaries",
   "review_status": "closed-with-basis",
   "review_basis": "Covered by session_bus drain at every task boundary and fetch-before-commit",
   "task_refs": []
  },
  "w1f-A2": {
   "required_outcome": "Under-asking visible",
   "review_status": "closed-with-basis",
   "review_basis": "Monitor under M1",
   "task_refs": []
  },
  "w1f-A3": {
   "required_outcome": "Stuck rules in code",
   "review_status": "closed-with-basis",
   "review_basis": "Knowledge-only: rowflow stuck and futility rules are already code-side",
   "task_refs": []
  },
  "w1g-A1": {
   "required_outcome": "Imbalanced arms flagged",
   "review_status": "preserved",
   "review_basis": "Task purpose matches the outcome; P2 / AEI-DROPS-MANIFEST",
   "task_refs": [
    {
     "owner": "handoffs/active/eval-tower-program.md",
     "task_id": "AEI-DROPS-MANIFEST",
     "task_text": "- [ ] **AEI-DROPS-MANIFEST** [non-inference] Emit a drops manifest (n scheduled, n scored, n dropped by reason) and graded_fraction = n_scored / n_attempted per arm with every eval-tower aggregate beside EV-18's ITT fields, and flag a quality delta whose two arms' graded fractions differ by more than 5 points (intake-2921 claims 0-1, intake-2935).",
     "acceptance": "cd /mnt/raid0/llm/epyc-orchestrator && python -m pytest tests/unit/test_eval_tower_drops_manifest.py -q passes, including a fixture where unequal graded fractions raise the flag"
    }
   ]
  },
  "w1g-A2": {
   "required_outcome": "Traces separate agent and grader actions",
   "review_status": "closed-with-basis",
   "review_basis": "Monitor: the eval-tower trajectory MONITOR trigger (first persisted agentic trajectory)",
   "task_refs": []
  },
  "w1g-A3": {
   "required_outcome": "Token accounting proven single-counted",
   "review_status": "preserved",
   "review_basis": "Task purpose matches the outcome; P2 / AEI-TOKEN-SPAN-RATIO",
   "task_refs": [
    {
     "owner": "handoffs/active/eval-tower-program.md",
     "task_id": "AEI-TOKEN-SPAN-RATIO",
     "task_text": "- [ ] **AEI-TOKEN-SPAN-RATIO** [non-inference] Check orchestrator token accounting for nested-span double counting: for one stored run per serving path (CPU llama-server role, MI210 role, streaming), compare summed per-call tokens against root-request tokens and record the ratio, fixing the aggregation if any ratio is not 1.0 (intake-2921 claim 2).",
     "acceptance": "progress/2026-11 note or handoff sub-bullet records the all-span/root-span token ratio for each of the three paths, and any ratio other than 1.0 has a linked fix commit"
    }
   ]
  },
  "w1g-A4": {
   "required_outcome": "No doubled HAL cost is cited",
   "review_status": "closed-with-basis",
   "review_basis": "Knowledge-only: recorded in intake-2915 contradicting_evidence",
   "task_refs": []
  },
  "w1h-A1": {
   "required_outcome": "Consistency computed where repeats exist",
   "review_status": "closed-with-basis",
   "review_basis": "Covered for reviewer run groups by _consistency_and_passk; resource CV waits on M2",
   "task_refs": []
  },
  "w1h-A2": {
   "required_outcome": "Calibration sub-metrics reported",
   "review_status": "closed-with-basis",
   "review_basis": "Covered by reviewer-calibration-accounting ECE/AUC",
   "task_refs": []
  },
  "w1h-A3": {
   "required_outcome": "Consistency not measured on identical repeats",
   "review_status": "closed-with-basis",
   "review_basis": "Covered: eval-tower records that temp+seed42 repeats are byte-identical and that Pass^k needs its own protocol id",
   "task_refs": []
  },
  "w1h-A4": {
   "required_outcome": "Robustness measured when a robustness protocol opens",
   "review_status": "closed-with-basis",
   "review_basis": "Monitor under M2",
   "task_refs": []
  },
  "w1h-A5": {
   "required_outcome": "Report sub-metrics only",
   "review_status": "closed-with-basis",
   "review_basis": "Declined: the paper itself calls its aggregation subjective; EPYC claim grammar is per metric",
   "task_refs": []
  },
  "w1b-A1": {
   "required_outcome": "Arms isolate one variable",
   "review_status": "preserved",
   "review_basis": "Built into the P5 design (one variable per arm)",
   "task_refs": [
    {
     "owner": "handoffs/active/knowledge-pipelines.md",
     "task_id": "AEI-KB-BREADCRUMB-AB",
     "task_text": "- [ ] **AEI-KB-BREADCRUMB-AB** [inference] Build a side kb-search index whose encoded chunk text is prefixed with the file path and full heading breadcrumb, and compare it with the production index on the K7 70-case pool (recall@10) plus an in-document subset, with the production index unchanged (intake-2924 claims 0-2, intake-2936, intake-2912).",
     "acceptance": "verdict tick records recall@3/5/10 for both indexes on the K7 pool and the in-document subset with the keep/drop decision under the stop rule"
    }
   ]
  },
  "w1c-A1": {
   "required_outcome": "No change",
   "review_status": "closed-with-basis",
   "review_basis": "Declined: measured -0.3 nDCG@10 on the same encoder family",
   "task_refs": []
  },
  "w1c-A2": {
   "required_outcome": "Keep/drop decision on breadcrumb encoding",
   "review_status": "preserved",
   "review_basis": "Task purpose matches the outcome; P5 / AEI-KB-BREADCRUMB-AB",
   "task_refs": [
    {
     "owner": "handoffs/active/knowledge-pipelines.md",
     "task_id": "AEI-KB-BREADCRUMB-AB",
     "task_text": "- [ ] **AEI-KB-BREADCRUMB-AB** [inference] Build a side kb-search index whose encoded chunk text is prefixed with the file path and full heading breadcrumb, and compare it with the production index on the K7 70-case pool (recall@10) plus an in-document subset, with the production index unchanged (intake-2924 claims 0-2, intake-2936, intake-2912).",
     "acceptance": "verdict tick records recall@3/5/10 for both indexes on the K7 pool and the in-document subset with the keep/drop decision under the stop rule"
    }
   ]
  },
  "w1c-A3": {
   "required_outcome": "LLM prefix tried only if cheap context helps",
   "review_status": "closed-with-basis",
   "review_basis": "Monitor: trigger is AEI-KB-BREADCRUMB-AB keep",
   "task_refs": []
  },
  "w1c-A4": {
   "required_outcome": "Trained embedder only on evidence",
   "review_status": "closed-with-basis",
   "review_basis": "Monitor under M5: NanoBEIR regression 67.7 to 59.2 is the gate",
   "task_refs": []
  },
  "w1d-A1": {
   "required_outcome": "Recorded",
   "review_status": "closed-with-basis",
   "review_basis": "Knowledge-only: intake-2925 verdict superseded",
   "task_refs": []
  },
  "w1d-A2": {
   "required_outcome": "No change",
   "review_status": "closed-with-basis",
   "review_basis": "Declined: no dense retriever consumer exists",
   "task_refs": []
  },
  "w1i-A1": {
   "required_outcome": "None",
   "review_status": "closed-with-basis",
   "review_basis": "Knowledge-only: run_shell allowlisting and CT-17 already split the classes",
   "task_refs": []
  },
  "w1i-A2": {
   "required_outcome": "No change",
   "review_status": "closed-with-basis",
   "review_basis": "Declined: the source has no measurement",
   "task_refs": []
  },
  "w1j-A1": {
   "required_outcome": "Static-attack ASR and utility of a sanitizer measured on our fixtures",
   "review_status": "preserved",
   "review_basis": "Task purpose matches the outcome; P4 / AEI-CT18-ARMD-RUN",
   "task_refs": [
    {
     "owner": "handoffs/active/harness-program.md",
     "task_id": "AEI-CT18-ARMD-PREP",
     "task_text": "- [ ] **AEI-CT18-ARMD-PREP** [non-inference] Prepare CT-18 arm D, a tool-output sanitizer in front of the agent: D-1 a detect-and-extract guardrail prompt run on the local worker role, D-2 the released DataFilter Llama-3.1-8B weights converted to GGUF with its special tokens checked, both given the trusted task and applied per JSON key (intake-2927, intake-2932, intake-2933).",
     "acceptance": "fixture-harness dry run on 3 IB2 items prints D-1 and D-2 sanitized outputs, and the GGUF tokenizer test shows the DataFilter special tokens round-trip"
    },
    {
     "owner": "handoffs/active/harness-program.md",
     "task_id": "AEI-CT18-ARMD-RUN",
     "task_text": "- [ ] **AEI-CT18-ARMD-RUN** [inference] Run CT-18 arms D-1 and D-2 on the IB2 24x3 fixtures with the worker and architect roles and report static-attack ASR, aligned-twin compliance, clean task_ok and clean-output false-removal rate per arm against arms A-C, worded per CT-20 (intake-2927 claims 0-3, intake-2931).",
     "acceptance": "verdict tick records ASR, aligned-twin compliance, task_ok and false-removal rate for D-1 and D-2 beside arms A-C on IB2 24x3, worded static-attack ASR on fixture set IB2"
    }
   ]
  },
  "w1j-A2": {
   "required_outcome": "Adaptive and semantic attacks once static arm D works",
   "review_status": "closed-with-basis",
   "review_basis": "Monitor: trigger is arm D static ASR below arms A-C",
   "task_refs": []
  },
  "w1j-A3": {
   "required_outcome": "Imported benchmarks are the corrected ones",
   "review_status": "closed-with-basis",
   "review_basis": "Knowledge-only: no AgentDojo import is planned",
   "task_refs": []
  },
  "w1k-A1": {
   "required_outcome": "Delegations keep untrusted data out of child instructions",
   "review_status": "preserved",
   "review_basis": "Task purpose matches the outcome; P4 / AEI-BOUNDARY-LAUNDER-LINT",
   "task_refs": [
    {
     "owner": "handoffs/active/harness-program.md",
     "task_id": "AEI-BOUNDARY-LAUNDER-LINT",
     "task_text": "- [ ] **AEI-BOUNDARY-LAUNDER-LINT** [non-inference] Add a static test that flags any delegation call site where a value from the untrusted-source list (tool output, worker output, doc text, retrieved chunk, report) is interpolated into a child role's natural-language instruction instead of a separate data field (intake-2928 claims 0-1).",
     "acceptance": "cd /mnt/raid0/llm/epyc-orchestrator && python -m pytest tests/unit/test_boundary_laundering_lint.py -q passes and lists each current call site as clean or allowlisted with a reason"
    }
   ]
  },
  "w1k-A2": {
   "required_outcome": "Plan-first cost sized before adoption",
   "review_status": "closed-with-basis",
   "review_basis": "Monitor under M3",
   "task_refs": []
  },
  "w1k-A3": {
   "required_outcome": "Typed return contract",
   "review_status": "closed-with-basis",
   "review_basis": "Covered by CM-3 typed return contract (harness-program)",
   "task_refs": []
  },
  "w1l-A1": {
   "required_outcome": "Fairness line on every arm report",
   "review_status": "preserved",
   "review_basis": "Task purpose matches the outcome; P3 / AEI-REV-FLIPS",
   "task_refs": [
    {
     "owner": "handoffs/active/reviewer-control-plane.md",
     "task_id": "AEI-REV-FLIPS",
     "task_text": "- [ ] **AEI-REV-FLIPS** [non-inference] Add per-arm fix and break counts (worker-wrong to reviewer-reject, worker-right to reviewer-reject) and a Kamoi-style fairness line (initial-prompt strength, no oracle stop, matched-token baseline present or absent) to the RM-2 arm report, computed offline from decisions already in the review ledger (intake-2930 claims 1-2, intake-2929 claim 4).",
     "acceptance": "cd /mnt/raid0/llm/epyc-orchestrator && python -m pytest tests/unit/test_reviewer_calibration_flips.py -q passes and the RM-2 report for the A1 48-row slice prints the new columns"
    }
   ]
  },
  "w1l-A2": {
   "required_outcome": "A1 closed unless the located arm lifts",
   "review_status": "preserved",
   "review_basis": "Task purpose matches the outcome; P3 / AEI-REV-A1-LOCATE-PROBE",
   "task_refs": [
    {
     "owner": "handoffs/active/reviewer-control-plane.md",
     "task_id": "AEI-REV-A1-LOCATE-PROBE",
     "task_text": "- [ ] **AEI-REV-A1-LOCATE-PROBE** [inference] Run one bounded diagnostic on the 48-row A1 slice with the incumbent A1 reviewer: arm L gives the gold defect location, arm P uses a comprehensive single-pass review prompt; report FA, FR and AUC per arm against the A1 baseline, then close A1 as a negative control unless arm L lifts (intake-2940 claims, intake-2937).",
     "acceptance": "verdict tick records FA/FR/AUC for arms L and P on the 48 rows with the pass/close decision under the stop rule"
    }
   ]
  },
  "w1l-A3": {
   "required_outcome": "Repair from objective feedback measured",
   "review_status": "closed-with-basis",
   "review_basis": "Monitor: trigger is RM-3 screening tier opening",
   "task_refs": []
  },
  "w1l-A4": {
   "required_outcome": "Decomposed verification measured where outputs decompose",
   "review_status": "closed-with-basis",
   "review_basis": "Monitor under M7",
   "task_refs": []
  },
  "w1m-A1": {
   "required_outcome": "Break rate visible",
   "review_status": "preserved",
   "review_basis": "Task purpose matches the outcome; P3 / AEI-REV-FLIPS",
   "task_refs": [
    {
     "owner": "handoffs/active/reviewer-control-plane.md",
     "task_id": "AEI-REV-FLIPS",
     "task_text": "- [ ] **AEI-REV-FLIPS** [non-inference] Add per-arm fix and break counts (worker-wrong to reviewer-reject, worker-right to reviewer-reject) and a Kamoi-style fairness line (initial-prompt strength, no oracle stop, matched-token baseline present or absent) to the RM-2 arm report, computed offline from decisions already in the review ledger (intake-2930 claims 1-2, intake-2929 claim 4).",
     "acceptance": "cd /mnt/raid0/llm/epyc-orchestrator && python -m pytest tests/unit/test_reviewer_calibration_flips.py -q passes and the RM-2 report for the A1 48-row slice prints the new columns"
    }
   ]
  },
  "w1m-A2": {
   "required_outcome": "No SFT on own traces",
   "review_status": "closed-with-basis",
   "review_basis": "Declined: the source's SFT controls gave delta at most +1.8 or negative (behaviour collapse)",
   "task_refs": []
  },
  "w1m-A3": {
   "required_outcome": "Sized only with a verifiable reward",
   "review_status": "closed-with-basis",
   "review_basis": "Monitor: trigger is a reviewer training lane with a verifiable reward",
   "task_refs": []
  },
  "w1m-A4": {
   "required_outcome": "A1 kept as anchor",
   "review_status": "preserved",
   "review_basis": "Task purpose matches the outcome; P3 / AEI-REV-A1-LOCATE-PROBE",
   "task_refs": [
    {
     "owner": "handoffs/active/reviewer-control-plane.md",
     "task_id": "AEI-REV-A1-LOCATE-PROBE",
     "task_text": "- [ ] **AEI-REV-A1-LOCATE-PROBE** [inference] Run one bounded diagnostic on the 48-row A1 slice with the incumbent A1 reviewer: arm L gives the gold defect location, arm P uses a comprehensive single-pass review prompt; report FA, FR and AUC per arm against the A1 baseline, then close A1 as a negative control unless arm L lifts (intake-2940 claims, intake-2937).",
     "acceptance": "verdict tick records FA/FR/AUC for arms L and P on the 48 rows with the pass/close decision under the stop rule"
    }
   ]
  },
  "w2a-A1": {
   "required_outcome": "Adaptive robustness measured before robustness wording",
   "review_status": "closed-with-basis",
   "review_basis": "Monitor under M6; CT-20 already forbids robustness wording from static fixtures",
   "task_refs": []
  },
  "w2a-A2": {
   "required_outcome": "ASR never reported alone",
   "review_status": "preserved",
   "review_basis": "Task purpose matches the outcome; P4 / AEI-CT18-ARMD-RUN",
   "task_refs": [
    {
     "owner": "handoffs/active/harness-program.md",
     "task_id": "AEI-CT18-ARMD-RUN",
     "task_text": "- [ ] **AEI-CT18-ARMD-RUN** [inference] Run CT-18 arms D-1 and D-2 on the IB2 24x3 fixtures with the worker and architect roles and report static-attack ASR, aligned-twin compliance, clean task_ok and clean-output false-removal rate per arm against arms A-C, worded per CT-20 (intake-2927 claims 0-3, intake-2931).",
     "acceptance": "verdict tick records ASR, aligned-twin compliance, task_ok and false-removal rate for D-1 and D-2 beside arms A-C on IB2 24x3, worded static-attack ASR on fixture set IB2"
    }
   ]
  },
  "w2b-A1": {
   "required_outcome": "D-1 prepared",
   "review_status": "preserved",
   "review_basis": "Task purpose matches the outcome; P4 / AEI-CT18-ARMD-PREP",
   "task_refs": [
    {
     "owner": "handoffs/active/harness-program.md",
     "task_id": "AEI-CT18-ARMD-PREP",
     "task_text": "- [ ] **AEI-CT18-ARMD-PREP** [non-inference] Prepare CT-18 arm D, a tool-output sanitizer in front of the agent: D-1 a detect-and-extract guardrail prompt run on the local worker role, D-2 the released DataFilter Llama-3.1-8B weights converted to GGUF with its special tokens checked, both given the trusted task and applied per JSON key (intake-2927, intake-2932, intake-2933).",
     "acceptance": "fixture-harness dry run on 3 IB2 items prints D-1 and D-2 sanitized outputs, and the GGUF tokenizer test shows the DataFilter special tokens round-trip"
    }
   ]
  },
  "w2b-A2": {
   "required_outcome": "D-1 prompt includes the definition",
   "review_status": "preserved",
   "review_basis": "Task purpose matches the outcome; P4 / AEI-CT18-ARMD-PREP",
   "task_refs": [
    {
     "owner": "handoffs/active/harness-program.md",
     "task_id": "AEI-CT18-ARMD-PREP",
     "task_text": "- [ ] **AEI-CT18-ARMD-PREP** [non-inference] Prepare CT-18 arm D, a tool-output sanitizer in front of the agent: D-1 a detect-and-extract guardrail prompt run on the local worker role, D-2 the released DataFilter Llama-3.1-8B weights converted to GGUF with its special tokens checked, both given the trusted task and applied per JSON key (intake-2927, intake-2932, intake-2933).",
     "acceptance": "fixture-harness dry run on 3 IB2 items prints D-1 and D-2 sanitized outputs, and the GGUF tokenizer test shows the DataFilter special tokens round-trip"
    }
   ]
  },
  "w2c-A1": {
   "required_outcome": "D-2 prepared",
   "review_status": "preserved",
   "review_basis": "Task purpose matches the outcome; P4 / AEI-CT18-ARMD-PREP",
   "task_refs": [
    {
     "owner": "handoffs/active/harness-program.md",
     "task_id": "AEI-CT18-ARMD-PREP",
     "task_text": "- [ ] **AEI-CT18-ARMD-PREP** [non-inference] Prepare CT-18 arm D, a tool-output sanitizer in front of the agent: D-1 a detect-and-extract guardrail prompt run on the local worker role, D-2 the released DataFilter Llama-3.1-8B weights converted to GGUF with its special tokens checked, both given the trusted task and applied per JSON key (intake-2927, intake-2932, intake-2933).",
     "acceptance": "fixture-harness dry run on 3 IB2 items prints D-1 and D-2 sanitized outputs, and the GGUF tokenizer test shows the DataFilter special tokens round-trip"
    }
   ]
  },
  "w2c-A2": {
   "required_outcome": "Clean false-removal reported",
   "review_status": "preserved",
   "review_basis": "Task purpose matches the outcome; P4 / AEI-CT18-ARMD-RUN",
   "task_refs": [
    {
     "owner": "handoffs/active/harness-program.md",
     "task_id": "AEI-CT18-ARMD-RUN",
     "task_text": "- [ ] **AEI-CT18-ARMD-RUN** [inference] Run CT-18 arms D-1 and D-2 on the IB2 24x3 fixtures with the worker and architect roles and report static-attack ASR, aligned-twin compliance, clean task_ok and clean-output false-removal rate per arm against arms A-C, worded per CT-20 (intake-2927 claims 0-3, intake-2931).",
     "acceptance": "verdict tick records ASR, aligned-twin compliance, task_ok and false-removal rate for D-1 and D-2 beside arms A-C on IB2 24x3, worded static-attack ASR on fixture set IB2"
    }
   ]
  },
  "w2f-A1": {
   "required_outcome": "Both retrieval modes measured",
   "review_status": "preserved",
   "review_basis": "Task purpose matches the outcome; P5 / AEI-KB-BREADCRUMB-AB",
   "task_refs": [
    {
     "owner": "handoffs/active/knowledge-pipelines.md",
     "task_id": "AEI-KB-BREADCRUMB-AB",
     "task_text": "- [ ] **AEI-KB-BREADCRUMB-AB** [inference] Build a side kb-search index whose encoded chunk text is prefixed with the file path and full heading breadcrumb, and compare it with the production index on the K7 70-case pool (recall@10) plus an in-document subset, with the production index unchanged (intake-2924 claims 0-2, intake-2936, intake-2912).",
     "acceptance": "verdict tick records recall@3/5/10 for both indexes on the K7 pool and the in-document subset with the keep/drop decision under the stop rule"
    }
   ]
  },
  "w2f-A2": {
   "required_outcome": "No change",
   "review_status": "closed-with-basis",
   "review_basis": "Declined: no in-corpus gain over paragraph chunking at about 1000x lower throughput (source Table 3)",
   "task_refs": []
  },
  "w2d-A1": {
   "required_outcome": "Operator decides the protocol change",
   "review_status": "preserved",
   "review_basis": "Measurement trust boundary is human-amendment-only",
   "task_refs": [
    {
     "owner": "handoffs/active/eval-tower-program.md",
     "task_id": "AEI-RERUN-ARM-OD",
     "task_text": "- [ ] **AEI-RERUN-ARM-OD** [operator-decision] Decide whether measurement/protocols/quality-eval.md P-AB-1 and P-PAIRED add a same-configuration rerun arm and report the rerun flip rate beside any scaffold, harness or reviewer-arm effect (intake-2934: reruns flipped 13% of tasks at the median, as many as a harness swap).",
     "acceptance": "operator decision recorded in this box's tick verdict, and if adopted a ratified protocol amendment exists"
    }
   ]
  },
  "w2d-A2": {
   "required_outcome": "Cost decomposed in scaffold comparisons",
   "review_status": "closed-with-basis",
   "review_basis": "Monitor under M2",
   "task_refs": []
  },
  "w2e-A1": {
   "required_outcome": "Drops manifest on every aggregate",
   "review_status": "preserved",
   "review_basis": "Task purpose matches the outcome; P2 / AEI-DROPS-MANIFEST",
   "task_refs": [
    {
     "owner": "handoffs/active/eval-tower-program.md",
     "task_id": "AEI-DROPS-MANIFEST",
     "task_text": "- [ ] **AEI-DROPS-MANIFEST** [non-inference] Emit a drops manifest (n scheduled, n scored, n dropped by reason) and graded_fraction = n_scored / n_attempted per arm with every eval-tower aggregate beside EV-18's ITT fields, and flag a quality delta whose two arms' graded fractions differ by more than 5 points (intake-2921 claims 0-1, intake-2935).",
     "acceptance": "cd /mnt/raid0/llm/epyc-orchestrator && python -m pytest tests/unit/test_eval_tower_drops_manifest.py -q passes, including a fixture where unequal graded fractions raise the flag"
    }
   ]
  },
  "w2e-A2": {
   "required_outcome": "Rule sensitivity known before confirmation tier",
   "review_status": "closed-with-basis",
   "review_basis": "Monitor under M7",
   "task_refs": []
  },
  "w2g-A1": {
   "required_outcome": "Arm P measured",
   "review_status": "preserved",
   "review_basis": "Task purpose matches the outcome; P3 / AEI-REV-A1-LOCATE-PROBE",
   "task_refs": [
    {
     "owner": "handoffs/active/reviewer-control-plane.md",
     "task_id": "AEI-REV-A1-LOCATE-PROBE",
     "task_text": "- [ ] **AEI-REV-A1-LOCATE-PROBE** [inference] Run one bounded diagnostic on the 48-row A1 slice with the incumbent A1 reviewer: arm L gives the gold defect location, arm P uses a comprehensive single-pass review prompt; report FA, FR and AUC per arm against the A1 baseline, then close A1 as a negative control unless arm L lifts (intake-2940 claims, intake-2937).",
     "acceptance": "verdict tick records FA/FR/AUC for arms L and P on the 48 rows with the pass/close decision under the stop rule"
    }
   ]
  },
  "w2g-A2": {
   "required_outcome": "Independent ground truth when C-CRAB saturates",
   "review_status": "closed-with-basis",
   "review_basis": "Monitor under M7",
   "task_refs": []
  },
  "w2h-A1": {
   "required_outcome": "No arm",
   "review_status": "closed-with-basis",
   "review_basis": "Declined: source has no correct-trace control and A1 AUC is near chance; reopen only if the location arm lifts",
   "task_refs": []
  },
  "w2i-A1": {
   "required_outcome": "Role recorded",
   "review_status": "preserved",
   "review_basis": "Task purpose matches the outcome; P3 / AEI-REV-A1-PRECHECK",
   "task_refs": [
    {
     "owner": "handoffs/active/reviewer-control-plane.md",
     "task_id": "AEI-REV-A1-PRECHECK",
     "task_text": "- [ ] **AEI-REV-A1-PRECHECK** [non-inference] Record two facts about the A1 self-review runner before any further A1 arm: whether the worker patch reaches the reviewer as user-role or assistant-role content, and whether the C-CRAB rows of the 48-row slice carry a gold defect location usable as an oracle hint (intake-2939, intake-2940).",
     "acceptance": "a sub-bullet under this box names the runner file:line for the message role and the count of the 48 rows with a gold defect location"
    }
   ]
  },
  "w2i-A2": {
   "required_outcome": "No arm",
   "review_status": "closed-with-basis",
   "review_basis": "Declined: flagging-only gains, needs the error location, false positives untested by the authors",
   "task_refs": []
  },
  "w2j-A1": {
   "required_outcome": "Arm L measured",
   "review_status": "preserved",
   "review_basis": "Task purpose matches the outcome; P3 / AEI-REV-A1-LOCATE-PROBE",
   "task_refs": [
    {
     "owner": "handoffs/active/reviewer-control-plane.md",
     "task_id": "AEI-REV-A1-LOCATE-PROBE",
     "task_text": "- [ ] **AEI-REV-A1-LOCATE-PROBE** [inference] Run one bounded diagnostic on the 48-row A1 slice with the incumbent A1 reviewer: arm L gives the gold defect location, arm P uses a comprehensive single-pass review prompt; report FA, FR and AUC per arm against the A1 baseline, then close A1 as a negative control unless arm L lifts (intake-2940 claims, intake-2937).",
     "acceptance": "verdict tick records FA/FR/AUC for arms L and P on the 48 rows with the pass/close decision under the stop rule"
    }
   ]
  },
  "w2k-A1": {
   "required_outcome": "Considered with a verifiable reward",
   "review_status": "closed-with-basis",
   "review_basis": "Monitor under M7 (same trigger as w1m-A3)",
   "task_refs": []
  }
 },
 "proposed_tasks": [
  {
   "owner": "handoffs/active/harness-program.md",
   "task_text": "- [ ] **AEI-CHAT-FINISH-REASON** [non-inference] Carry the backend completion_reason into the /chat response as finish_reason plus a truncated flag, so a length-cut answer is returned marked truncated instead of as a complete final answer (intake-2907 discovery; gap at src/api/models/responses.py @ 1cc2043, no finish_reason field)."
  },
  {
   "owner": "handoffs/active/harness-program.md",
   "task_text": "- [ ] **AEI-TRUNC-NOTICE** [non-inference] Make the three '[... truncated at N chars]' markers in src/llm_primitives/primitives.py say how to get the rest (the spilled file path with peek/grep, or a narrower request), matching the REPL spill footer (intake-2911 claim 1)."
  },
  {
   "owner": "handoffs/active/eval-tower-program.md",
   "task_text": "- [ ] **AEI-DROPS-MANIFEST** [non-inference] Emit a drops manifest (n scheduled, n scored, n dropped by reason) and graded_fraction = n_scored / n_attempted per arm with every eval-tower aggregate beside EV-18's ITT fields, and flag a quality delta whose two arms' graded fractions differ by more than 5 points (intake-2921 claims 0-1, intake-2935)."
  },
  {
   "owner": "handoffs/active/eval-tower-program.md",
   "task_text": "- [ ] **AEI-TOKEN-SPAN-RATIO** [non-inference] Check orchestrator token accounting for nested-span double counting: for one stored run per serving path (CPU llama-server role, MI210 role, streaming), compare summed per-call tokens against root-request tokens and record the ratio, fixing the aggregation if any ratio is not 1.0 (intake-2921 claim 2)."
  },
  {
   "owner": "handoffs/active/eval-tower-program.md",
   "task_text": "- [ ] **AEI-RERUN-ARM-OD** [operator-decision] Decide whether measurement/protocols/quality-eval.md P-AB-1 and P-PAIRED add a same-configuration rerun arm and report the rerun flip rate beside any scaffold, harness or reviewer-arm effect (intake-2934: reruns flipped 13% of tasks at the median, as many as a harness swap)."
  },
  {
   "owner": "handoffs/active/reviewer-control-plane.md",
   "task_text": "- [ ] **AEI-REV-FLIPS** [non-inference] Add per-arm fix and break counts (worker-wrong to reviewer-reject, worker-right to reviewer-reject) and a Kamoi-style fairness line (initial-prompt strength, no oracle stop, matched-token baseline present or absent) to the RM-2 arm report, computed offline from decisions already in the review ledger (intake-2930 claims 1-2, intake-2929 claim 4)."
  },
  {
   "owner": "handoffs/active/reviewer-control-plane.md",
   "task_text": "- [ ] **AEI-REV-A1-PRECHECK** [non-inference] Record two facts about the A1 self-review runner before any further A1 arm: whether the worker patch reaches the reviewer as user-role or assistant-role content, and whether the C-CRAB rows of the 48-row slice carry a gold defect location usable as an oracle hint (intake-2939, intake-2940)."
  },
  {
   "owner": "handoffs/active/reviewer-control-plane.md",
   "task_text": "- [ ] **AEI-REV-A1-LOCATE-PROBE** [inference] Run one bounded diagnostic on the 48-row A1 slice with the incumbent A1 reviewer: arm L gives the gold defect location, arm P uses a comprehensive single-pass review prompt; report FA, FR and AUC per arm against the A1 baseline, then close A1 as a negative control unless arm L lifts (intake-2940 claims, intake-2937)."
  },
  {
   "owner": "handoffs/active/harness-program.md",
   "task_text": "- [ ] **AEI-CT18-ARMD-PREP** [non-inference] Prepare CT-18 arm D, a tool-output sanitizer in front of the agent: D-1 a detect-and-extract guardrail prompt run on the local worker role, D-2 the released DataFilter Llama-3.1-8B weights converted to GGUF with its special tokens checked, both given the trusted task and applied per JSON key (intake-2927, intake-2932, intake-2933)."
  },
  {
   "owner": "handoffs/active/harness-program.md",
   "task_text": "- [ ] **AEI-CT18-ARMD-RUN** [inference] Run CT-18 arms D-1 and D-2 on the IB2 24x3 fixtures with the worker and architect roles and report static-attack ASR, aligned-twin compliance, clean task_ok and clean-output false-removal rate per arm against arms A-C, worded per CT-20 (intake-2927 claims 0-3, intake-2931)."
  },
  {
   "owner": "handoffs/active/harness-program.md",
   "task_text": "- [ ] **AEI-BOUNDARY-LAUNDER-LINT** [non-inference] Add a static test that flags any delegation call site where a value from the untrusted-source list (tool output, worker output, doc text, retrieved chunk, report) is interpolated into a child role's natural-language instruction instead of a separate data field (intake-2928 claims 0-1)."
  },
  {
   "owner": "handoffs/active/harness-program.md",
   "task_text": "- [ ] **AEI-HTTPPOST-GUARD** [non-inference] Apply the SEC-EXEC-3 web_guard destination check to http_post (orchestration/tools/web.py), which today posts to any URL while roles holding the web category also read untrusted pages (intake-2907 discovery; intake-2928 context)."
  },
  {
   "owner": "handoffs/active/knowledge-pipelines.md",
   "task_text": "- [ ] **AEI-KB-BREADCRUMB-AB** [inference] Build a side kb-search index whose encoded chunk text is prefixed with the file path and full heading breadcrumb, and compare it with the production index on the K7 70-case pool (recall@10) plus an in-document subset, with the production index unchanged (intake-2924 claims 0-2, intake-2936, intake-2912)."
  }
 ]
}
```
