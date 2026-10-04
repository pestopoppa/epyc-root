# Decision tools intake — narrow EPYC implementation plan

Revised 2026-10-04 after inspecting the project repositories. **Stage 3: awaiting approval; Stage 4 has not started.** This version replaces the previous nine-task contracts/validators programme. Its outcomes are small changes to existing operational paths: preserve REPL state, avoid checkpointing a timed-out interpreter, finish the already-owned typed shadow, expose actual prefill/cache counts, and correct two evaluation-accounting gaps and one extractor defect.

There is no new framework, receipt platform, provenance subsystem, training campaign, sandbox migration or model-port campaign. Two changes refine existing TD-29 tasks; five are new bounded fixes under existing owners. Research recommendations remain fully accounted for in the appendix, not automatically converted into engineering work.

## What EPYC actually has

Governance inspected: this isolated lane at `162fad60ad2251997525479c5ace2885f6f5f573`, based on `ab84e579ee373c435c5b0c449f1da2b2529dc50e`. The shared root checkout is older, `db398a70`; its README and some campaign descriptions cannot establish current state. Implementation inspected: orchestrator `ff92a580ea1a0a35c7eb803a4ad325d63bc810b1` (2026-10-04 02:03:33 UTC), research `412e8fc11d153554354f51c9f9f70b9c984578f8`. The running API's read-only version endpoint reports launch SHA `ff92a580`; this confirms API source identity, not every feature flag or model's health.

| Track | Existing architecture | Consequence for this intake |
|---|---|---|
| Harness | OpenCode is the selected shell; `/v1` supports client-owned tools and explicit role overrides. `/chat` runs direct, REPL, edit or delegated execution. | Strengthen these paths; do not reopen harness selection or design another shell. |
| Orchestration | Role/stack compilation, capacity/placement admission, escalation, typed Choice/Score/Noul, host-owned prepared actions, receipts and prefix routing exist. | Complete TD-29; do not rebuild menus, authority, scoring or caches. |
| Memory/learning | Episodic retrieval and Q-value updates are distinct from the optional NumPy routing MLP and from language-model SFT. UTM is a provenance/query service, not a training rollout engine. | Correct the extractor; do not label generic traces as GRPO data or replace memory architecture. |
| Inference | CPU-first EPYC plus MI210; Flash-Next is architect-general, the 27B shares critic/coder/ingest roles. Production v10 is frozen and binaries resolve through the kernel store. | Role selection does not imply another model load. Do not infer savings from model size alone, duplicate DFlash/KV work, or touch frozen kernels. |
| Evidence/beliefs | Literature ingestion, corrections/dependencies, use-policy gates, shared measurement grading and bounded AutoPilot planner bridges exist. | Retain source qualifications there. They are not a mandate for another evidence platform. |

Implementation entry points: [client tools](/workspace/repos/epyc-orchestrator/src/api/routes/openai_compat.py:590), [chat execution](/workspace/repos/epyc-orchestrator/src/api/routes/chat.py:762), [routing](/workspace/repos/epyc-orchestrator/src/api/routes/chat_pipeline/routing_decision.py:260), [hybrid router](/workspace/repos/epyc-orchestrator/orchestration/repl_memory/hybrid_router.py:388), [kernel resolution](/workspace/repos/epyc-orchestrator/src/registry/kernel_paths.py:68).

The automatic answer-review gate was removed under its existing DROP verdict; do not add a generic referee to replace it. Routing expansion, LRC-1/LRC-2 and DAR-LAT remain frozen until autopilot has learned on the swapped stack AND UFH-13 reopens. TD-28 also requires v11. Closed-set tool arguments remain shadow-only until v11. Native experiments use the agreed champion CPU sidecar; JSON-only experiments use coordinated MI210 windows. This plan authorizes no runtime change by its preparation.

## Implementation outcomes

For all seven bounded changes, the baseline is the inspected implementation at the pinned orchestrator HEAD. Freeze fixture inputs and expected results in tests; retain named case outcomes in the existing test report; include failing, missing, delayed and refusal cases in the denominator; require all invariants below with existing regression suites green. An empirical holdout is inapplicable to field propagation and lifecycle/filter invariants: independently prepared negative/mutation fixtures supply the falsifiers instead. This is conformance, not evidence of a measured speed or quality uplift. Only P1's already-owned M4 follow-through is empirical, and its six controls are stated below.

### P1 — Finish TD-29 without taxing or changing executed tool calls

**Context and hypothesis.** The project already owns the right experiment. Current `_dispatch_tool()` synchronously selects typed arguments and replaces the model's arguments after acceptance; the selector defaults to native. That implementation is not the required bounded JSON shadow. Also, `/completion` cache/prefill counts do not reach the existing recorder consistently. A bounded, non-authoritative shadow makes tool selection testable without changing results or waiting for the selector. Accurate counts allow TD-29.M4 to determine whether repeated prefill—not decode—is the avoidable cost.

**Objective.** Keep model-provided arguments on the operational path; record the alternative and actual outcome asynchronously. Recover server-reported prompt/cache counts for both batch and streaming completion transports. Any latency improvement from prefix reuse remains a hypothesis until measured.

**Strong recommendation.** Refine the existing TD-29 and TD-29.M0a; do not add another screen or receipt schema. Reuse bounded routing-shadow infrastructure, prepared actions, `decision_receipt.v1` and `call_recorder`. Explicitly use JSON before v11. Do not change slot-pinning defaults.

**Code evidence.** [argument replacement](/workspace/repos/epyc-orchestrator/src/repl_environment/context.py:630), [native default](/workspace/repos/epyc-orchestrator/src/typed_decisions/tool_args_integration.py:151), [bounded shadow](/workspace/repos/epyc-orchestrator/src/typed_decisions/shadow.py:290), [chat-only count propagation](/workspace/repos/epyc-orchestrator/src/llm_primitives/inference.py:1600), [server cache count](/workspace/repos/epyc-orchestrator/src/backends/llama_server.py:549). Flags default off; a production substitution incident is not established.

**Research justification.** Clef and the other reviewed decision readouts are candidates for existing TD-23, not proof of a better EPYC backend. Retry-inclusive and timing-scope lessons apply immediately to TD-29's existing cost measurement. Discussion: intake-1855#record, intake-1859#record, intake-1865#record, intake-1891#record. Joint head semantics and calibration remain candidate-specific constraints.

**Exact existing-task refinements** under [typed-decision-plane.md](../handoffs/active/typed-decision-plane.md), TD-29:
- **TD-29 scope refinement:** Implement bounded, non-blocking tool-argument shadow; execute the original arguments unchanged; explicitly use JSON until v11; append proposed arguments, executed arguments and outcome through the existing decision receipt. Drop/refuse shadow work on saturation or failure without altering the tool result.
- **TD-29.M0a scope refinement:** Carry server-reported `prompt_n`, `cache_n` and streaming `prompt_ms` through raw completion results and primitives metadata into the existing recorder. Preserve absent values as unknown; do not estimate or substitute `tokens_cached`.

**Acceptance.** Mocked blocking/failing/saturated selectors never alter executed kwargs or make dispatch await them. Flag-off makes no selector call. Delayed results bind to the original action/outcome. Batch/stream fixtures with known timings produce exact counts; missing timings remain unknown. Existing permissions, freshness/fallback and retry tests remain green. Direct consumers are REPL dispatch and TD-29's pilot; TD-23 and the existing evidence adapter consume their existing outputs.

**Performance follow-through.** TD-29.M4 already owns paired cache inspection; do not create another task. Use its current sidecar/gate, frozen case manifest, current same-server incumbent, raw per-case outputs/counts including all errors, development versus held-out cases, and complete failure/abstention denominator. Predeclare the stop rule before collection: reject any result/argument regression; report paired prefill and total-wall changes with constitution-required intervals, and claim benefit only when the applicable interval clears zero. If reuse is absent, identify and fix only the actual prefix break; if present, make no cache rewrite. No routing or replacement promotion follows.

### P2 — Preserve existing REPL state and stop saving uncertain timed-out state

**Context and hypothesis.** CPython globals persist in one environment, and authenticated pickle/SQLite/fencing already exist. But `checkpoint()` emits `pickled_globals` while both checkpoint constructors omit that field. The store supports it, so non-JSON values can be serialized successfully and then silently lost across requests. Separately, `asyncio.wait_for(to_thread(...))` stops waiting, not the executing thread; SIGALRM is skipped in that thread. Checkpointing or continuing to use that environment after timeout is unsafe.

**Objective.** Supported non-JSON values survive the existing save/store/restore path. An environment with a timed-out worker is terminal and cannot supply another execution or durable checkpoint.

**Strong recommendation.** Fix the field plumbing and add a terminal/poisoned state to the current interpreter lifecycle. Do not migrate to Monty or redesign serialization. Timeout poisoning prevents reuse/persistence; it does not kill the thread, confine host callbacks or undo an already dispatched effect.

**Code evidence.** [checkpoint producer](/workspace/repos/epyc-orchestrator/src/repl_environment/state.py:526), [API constructor](/workspace/repos/epyc-orchestrator/src/api/routes/chat_pipeline/repl_executor.py:907), [persister constructor](/workspace/repos/epyc-orchestrator/src/session/persister.py:190), [store support](/workspace/repos/epyc-orchestrator/src/session/sqlite_store.py:787), [thread timeout](/workspace/repos/epyc-orchestrator/src/graph/helpers.py:1364), [skipped signal](/workspace/repos/epyc-orchestrator/src/repl_environment/environment.py:1452). These are source-level defects/limitations, not measured incident rates.

**Research justification.** Monty's snapshot/lifecycle findings direct attention to actual persistence and disposal, not another requirements matrix. EPYC already avoids restarting/replaying its interpreter every turn; publisher startup comparisons do not establish a local speedup. Discussion: intake-1850#record, intake-1864#record. Signed restoration and D-f remain completed; D-f1 still owns live lease verification. D-g's uncertain-side-effect journal remains open, not falsely described as complete.

Paste-ready additions under [repl-session-memory-maturity.md](../handoffs/active/repl-session-memory-maturity.md), “Research Intake Update 2026 10 04”:

- [ ] **D-RI-PICKLE-PASS — Preserve pickled_globals through both existing checkpoint constructors.** Forward the already-signed payload through /chat and SessionPersister into Checkpoint; preserve size limits, unavailable-variable reporting, protocol normalization and fenced writes. Add a regression traversing each producer, SQLite save/load and restore for one supported non-JSON value, plus tampered/unsupported payload refusal.
- [ ] **D-RI-TIMEOUT-STATE — Make a timed-out REPL environment terminal for reuse and persistence.** Mark timeout at the worker-await boundary, stop further execution in that environment and suppress its API/persister checkpoint writes. Test a bounded delayed worker that finishes after the timeout; no subsequent execute or checkpoint may accept its namespace. Keep lease cleanup and timeout reporting intact; do not claim worker termination or host-effect cancellation.

**Acceptance and consumers.** Tests must fail against the current constructors and timeout path, then pass through the real existing store boundary. Include legacy checkpoints, tampering, lease/fencing loss and a delayed-worker case; never use an infinite background fixture. Consumers are /chat resume, SessionPersister and graph REPL execution. No model calls or holdout are needed for these deterministic invariants. No broader interpreter project is implied.

### P3 — Make missing capture and reconnect cost visible in existing evaluation results

**Context and hypothesis.** EvalTower already separates grading from generation, catches token-capture exceptions, preserves answers for rescoring, appends/fsyncs question sidecars and classifies failures. FineEnvs' external grade-loss/overwritten-file problems are therefore not established local bugs. Two smaller gaps do exist: sidecar initialization/append/completion failures only warn, and a successful reconnect drops its locally accumulated attempt/wait history.

**Objective.** A batch with valid grades but incomplete durable capture must say so. A recovered request must retain its actual reconnect count/wait alongside the existing exogenous retry metadata. This improves diagnosis and prevents undercounting recovery overhead; it promises no training gain.

**Code evidence.** [sidecar failures](/workspace/repos/epyc-orchestrator/scripts/autopilot/eval_tower.py:5115), [append handling](/workspace/repos/epyc-orchestrator/scripts/autopilot/eval_tower.py:5139), [reconnect returns](/workspace/repos/epyc-orchestrator/scripts/benchmark/seeding_orchestrator.py:1110), [existing retry layer](/workspace/repos/epyc-orchestrator/scripts/autopilot/resilient_http.py:89).

**Research justification.** Apply the grade-versus-capture and retry-inclusive accounting lessons to the actual local gaps. Do not build token-perfect GRPO export: no inspected UTM/EvalTower consumer implements that training contract. Discussion: intake-1856#record, intake-1867#record, intake-1891#record; intake-1887#record and intake-1896#record qualify prospective training, not these patches.

Paste-ready additions under [eval-tower-verification.md](../handoffs/active/eval-tower-verification.md), “Research Intake Update 2026 10 04”:

- [ ] **EV-RI-CAPTURE-STATUS — Expose question-sidecar persistence status in existing batch details.** Report writer initialization, successful/failed row appends and completion-marker state, with bounded error reasons. Preserve every in-memory grade and existing failure disposition; report an incomplete archive explicitly rather than presenting in-memory completion as durable capture.
- [ ] **EV-RI-RECONNECT-COST — Retain reconnect attempts and cumulative backoff in existing question metadata.** Carry counts, waited seconds and bounded failure reasons through every success/terminal return from call_orchestrator_forced, alongside resilient_post's separate exogenous retry count. Preserve current retry eligibility, budgets, results and grading semantics; do not sum unlike nested attempt counts as independent requests.

**Acceptance.** Fault-inject writer creation, one append and completion-marker failure: grades unchanged, durable counts/status exact. Fake connection failures followed by success and exhausted budget: counts/wait exact, non-reconnectable errors unretried. Cover the direct and watcher paths. Deterministic fixtures replace empirical holdout; count all fixtures, including degraded cases. Consumers are batch details, question metadata and their existing summaries, not a new publication or training system.

### P4 — Honor the routing extractor's selected source and min_updates

**Context and hypothesis.** The MLP data path already normalizes actions from live stack priors and builds 1,031-dimensional embedding/context features with Q as a sample weight. However, an existing default cached NPZ silently takes precedence over the caller's DB and ignores `min_updates`; the output still records that requested filter. The DB branch applies it. Correcting source/filter semantics prevents inadvertent use of the wrong or insufficiently updated training cohort.

**Objective.** The requested DB is used unless a cached snapshot is explicitly selected. A positive `min_updates` cannot silently pass on a snapshot lacking update counts.

**Strong recommendation.** Correct this one extractor; retain feature ordering, action normalization and Q weighting. No new provenance schema, re-embedding run, retraining, SDM installation or flag enabling.

**Code evidence.** [source selection and cached loop](/workspace/repos/epyc-orchestrator/scripts/graph_router/extract_training_data.py:98), [DB filter](/workspace/repos/epyc-orchestrator/scripts/graph_router/extract_training_data.py:145). The inspected cache lacks update counts. This establishes inconsistent source/filter semantics, not which artifact trained a running model.

**Research justification.** SDM's fit/context-cache separation is useful when applied to this actual snapshot-selection defect. An SDM challenger would replace an existing classifier, not create another memory substrate; alternative-action outcomes still require real evidence. Discussion: intake-1852#record.

Paste-ready addition under [learned-routing-controller.md](../handoffs/active/learned-routing-controller.md), “Research Intake Update 2026 10 04”:

- [ ] **LRC-RI-EXTRACT-SOURCE — Make routing-data extraction honor explicit source and update-count filtering.** Use the requested DB by default; select an NPZ only through the existing explicit embeddings-file argument. Reject a positive min_updates when the selected snapshot cannot enforce it, or enforce it from an actual captured update-count array. Add DB/NPZ branch tests proving the effective source/filter and included/excluded counts; retain action/feature ordering and weights. No live-store mutation, re-embedding, training or routing enablement.

**Acceptance.** With a default cache present, a DB request still uses the test DB. Explicit snapshot selection works at zero threshold; a positive threshold without update counts refuses before output. Equivalent eligible DB/snapshot fixtures preserve row/action/feature semantics. Existing callers must either explicitly choose their snapshot or keep DB behavior. Tests use temporary stores and small arrays, not the live corpus. Direct consumers are extraction and the existing training CLI; frozen learning tasks remain frozen.

## Why the general critiques are beliefs, not work packets

K1–K11 retain qualifications and source corrections through the existing research-intake literature path. Use anchored claims and their corrections/dependencies to judge an actual proposal; do not manufacture a universal contract to encode every warning.

The code already provides [literature ingestion](/workspace/scripts/vidya/adapters/research_intake.py:421), [use-policy evaluation](/workspace/scripts/vidya/gate.py:170), and AutoPilot's [settled-ground/KV evidence bridge](/workspace/repos/epyc-orchestrator/scripts/autopilot/vidya_planner_bridge.py:26). Planner reliance on supplied KV evidence is explicitly archived. These consumers are bounded; there is no verified general “all literature automatically changes agent scope” connection. Do not claim one, add a new bridge here, change warrant grades, or let literature observations overrule operator freezes.

For this campaign, source-qualified beliefs narrow the proposal now: calibration is not correctness, a sandbox does not confine delegated host authority, scalar dashboards are not GRPO trajectories, and looped prefill is not faster decode. Their operational effect is to prevent unjustified backend selection, migration, training or inference claims—not to create engineering tasks. The four actual implementation gaps above have local code evidence independently of those critiques.

| Knowledge | Use |
|---|---|
| K1 Frameworks essay | Architectural hypothesis only; no framework migration premise. |
| K2 Corrected source claims | Keep release, source-tree, scoring-edition and publication-scope corrections; no extra reproduction. |
| K3 Attribution | Historical quotations and current vendor pages have separate provenance. |
| K4 Hosted products | Schema/economics context only; no paid or hosted calls. |
| K5 Existing authority | Prepared actions, permissions/freshness and fallback already have owners; do not duplicate. |
| K6 Training objective | Correctness-gated efficiency is a candidate objective, not a reason to start weight training. |
| K7 Decision qualifications | Calibration targets, invalid/raw mass, joint/sibling effects, benchmark denominators and resolved identity constrain existing TD-18/TD-23. No new receipt, fixture runner or cohort importer. |
| K8 Monty qualifications | Version/security history, module compatibility, snapshots and host waits constrain any later specific backend proposal. P2 fixes local state continuity/lifecycle only. |
| K9 Training/capture qualifications | Exact IDs/logprobs/masks, exposure/selection and publication provenance constrain real training use. Existing local grade/retry retention is preserved. |
| K10 Tabular qualifications | Fitted-state/backend/assets/splits/explanations constrain a future SDM challenger; no generic artifact validator now. |
| K11 Looped qualifications | Teacher binding, cache construction, finite-depth assumptions and prefill-only timing constrain any later checkpoint comparison; no teacher envelope or port now. |

## Candidate notes — no new campaign or active checkbox

These names preserve recommendation coverage, not implementation programmes. Reconsider only at an existing owner's concrete decision, and bound any later scope independently.

| Record | Existing owner and specific condition |
|---|---|
| M1 Local decision backend | TD-23: one local compatible candidate and sealed workload are available in the existing coordinated window. Clef/Flash/AutoTrust remain candidates; no model is selected or hosted arm added here. |
| M2 Monty | REPL owner: a specific workload needs disposable/resource-limited execution that current CPython cannot supply, and its imports/callbacks/snapshot requirements can be met. No adapter, inventory campaign or migration now. |
| M3 Multi-harness weight training | Existing harness/training owner: an actual approved weight-training consumer requires these rollouts. Current UTM/AP-27 products must not be called token-perfect training data. No training/export platform now. |
| M4 SDM challenger | LRC owner: the existing learning/UFH-13 gates reopen and a valid outcome-labelled cohort and eligible asset/backend are available. No fitting, explanation or license-review campaign now. |
| M5 Looped checkpoint | Reasoning-compression owner: a usable instruct checkpoint/runtime meets its existing lineage trigger and a measured prefill bottleneck makes a comparison relevant. No manifest code, port or training now. |
| M6 External score | TD-23 owner: a particular external score actually affects its local candidate choice and cannot be resolved from already-reviewed evidence. No general publication reconciler. |
| M7 Provisional narrative | A particular narrative claim is needed as factual rationale; qualify it in a separate intake before use. No fourth wave in this campaign. |
| M8 Hardware/modality | An actual selected local candidate needs that released execution path or modality. Confirm that specific path; do not start a generic compatibility programme. |

## Approval and exact Stage 4 filing scope

Approval applies to this narrowed filing plan. Stage 4 amends existing handoffs and intake dispositions; it is not permission to immediately run seven code changes on the shared host.

- Update existing TD-29 and TD-29.M0a with P1's scope refinements; do not duplicate their checkboxes.
- Add exactly five unchecked tasks: D-RI-PICKLE-PASS, D-RI-TIMEOUT-STATE, EV-RI-CAPTURE-STATUS, EV-RI-RECONNECT-COST, LRC-RI-EXTRACT-SOURCE.
- File the relevant K/M prose under the existing typed, REPL, EvalTower, LRC and reasoning-compression owners. UTM receives only the clarification that existing pairing is not a GRPO exporter; UTM-P1a.3 remains its existing task.
- No new stub, domain/master row, replacement current priority, schema programme, or Vidya producer campaign. Each owner already has exactly one domain-index row. No completed checkbox is re-ticked.
- Implementation patches/tests remain with their existing subsystem owner. P1, P2, P3 and P4 have disjoint primary surfaces and can be developed concurrently; live inference/reloads remain coordinated. Parent alone applies shared handoff/index/intake updates.
- Use existing test/report and measurement paths. Before a future new measurement producer emits decision-bearing evidence, wire that actual producer using the standing Vidya rule and existing shared grader; do not pre-build producer hooks for unselected technologies.

Exact proposed record metadata is below. `integrated_existing` requires that the corresponding refinement/fix/candidate prose actually lands; merely mentioning a consumer is not integration. All `handoffs_created` remain empty. Preserve precise existing corrections, anchors and prior records; do not mint new source entries or change trust boundaries. Numeric suffixes below refer to the already-listed record inventory, not whole-entry factual warrants.

| Proposed disposition | Record suffixes | Exact handoffs_updated after application |
|---|---|---|
| integrated_existing | 1855, 1859, 1863, 1865, 1875, 1882, 1884, 1885 | typed-decision-plane.md |
| integrated_existing | 1850, 1864, 1886 | repl-session-memory-maturity.md |
| integrated_existing | 1856, 1867 | eval-tower-verification.md; unified-trace-memory-service.md |
| integrated_existing | 1891 | typed-decision-plane.md; eval-tower-verification.md |
| integrated_existing | 1852, 1881, 1888, 1889, 1890 | learned-routing-controller.md |
| integrated_existing | 1853, 1854 | reasoning-compression.md |
| awaiting_dive | 1851, 1857, 1858, 1860, 1861 | [] |
| knowledge_only | 1862, 1866, 1868, 1869, 1870, 1871, 1872, 1873, 1874, 1876, 1877, 1878, 1879, 1880, 1883, 1887, 1892, 1893, 1894, 1895, 1896, 1897, 1898, 1899 | [] |

Use the corresponding K/M reason as disposition_evidence, retaining mixed-action nuance where relevant. Provisional records keep empty integration lists and the factual-use prohibition. Intake-1470's prior state and re-encounter note are unchanged. Reconcile the checkpoint's mapping/steering to this reviewed plan at Stage 4.

## Operator steering and coverage

Three Stage 2 waves are complete (15 source/code reviews each); no fourth wave was performed in this repository grounding pass. Fifty new records, intake-1850#record through intake-1899#record, retain 44 dive-verified, one precisely dive-overturned and five provisional records. Independent machine source checking is not empirical reproduction or human warrant. All 137 prior recommendations, including 24 Stage 1 rows, remain in the appendix. This revision adds local gap findings; it does not discard research or dismiss a technique as not applicable.

SCOPE-1 (preserved verbatim):

> Accept all recommended deep dives automatically without asking me for input. Do not perform more than three district stage 2 dive waves. When you reach stage 3, all recommended actionables should be included in the plan

“District” is treated as “distinct.” Coverage means every recommendation has a disposition, not every methodological suggestion becomes engineering scope.

SCOPE-2 (2026-10-04, preserved verbatim):

> "Its immediate objective is not to select a winning decision model, replace the REPL with Monty, or reproduce a training paper. It is to establish the contracts and evidence needed to make those decisions reliably." - what is this meta? The plan better be about actionable implementation outcomes that would benefit operational performance and robustness of harness/orchestration/inference architecture tracks of this EPYC project.
>
> "A decision model may return probabilities without establishing their calibration. A sandbox may isolate execution without constraining delegated host authority. A training dashboard may publish results without supplying valid training trajectories. A fitted classifier may lack evidence about which features were available when a decision occurred. A looped-model checkpoint may have valid hashes without being bound to the correct teacher.
> The plan therefore concentrates on reusable contracts, validators and fixtures. These remain useful whether we eventually adopt the particular technology or not. The frameworks essay contributes architectural context, but it does not establish a reason to migrate frameworks." - plans need to be far narrower. Hypotheses of improvements with their context, objectives, justification, and any strong implementation recommendations that may have surfaced as part of the research intake process.
>
> High level meta critiques should be affect project scope through agent (belief kernel driven?) Beliefs

SCOPE-3:

> You're effectively recommending / designing major future work campaigns

SCOPE-4:

> Look through the project repo

SCOPE-5:

> Make sure you understand what you're working with

SCOPE-2 maps to P1–P4 and K1–K11; SCOPE-3 maps to removal of the generic programmes and non-active M notes; SCOPE-4/5 map to the pinned repository grounding above. SCOPE-1 maps to completed waves and the complete appendix. Stage 3 writes only this plan; append the new steering to the session checkpoint at the approved Stage 4 boundary.

This plan's revised mapping supersedes the earlier P1–P5 mapping retained in the untouched session checkpoint. That checkpoint is historical until Stage 4 reconciles it; it is not authority to reinstate the removed generic tasks.

## Complete recommendation mapping

The retained proposal column records what research suggested, not an instruction to implement its original broad wording. The terminal mapping is authoritative: existing features and methodological cautions become K beliefs; unselected technologies become M notes; P actions are only the narrow patches/refinements above. In particular a P mapping does not approve the rest of a broad original proposal. No recommendation is an inferred operator decline.

| Ledger row | Source or review | Retained recommendation | Terminal plan mapping |
|---|---|---|---|
| S1-1850-1 | intake-1850#record | [unverified] Dive callbacks, worker deadlines, authenticated snapshots and disposal after terminal resource errors. | primitive-now → P2 |
| S1-1850-2 | intake-1850#record | [unverified] Compare supported modules and checkpoint semantics with the existing REPL before proposing an adapter. | knowledge-only → K8 |
| S1-1851-1 | intake-1851#record | [unverified] Map the standardization hypothesis to existing typed contracts and owners; do not infer a framework migration benefit from this essay. | knowledge-only → K1 |
| S1-1852-1 | intake-1852#record | [unverified] Dive tabular CPU/ROCm paths, relational sampler dispatch and weight licenses before choosing component adoption. | knowledge-only → K10 |
| S1-1852-2 | intake-1852#record | [unverified] Consider one provenance-preserving adapter over existing routing/reward feature manifests; exclude outcome-derived fields from prediction inputs. | knowledge-only → K10 |
| S1-1853-1 | intake-1853#record | [unverified] Dive convergence assumptions and endpoint/cache construction; review manifest binding before proposing any reproduction. | knowledge-only → K11 |
| S1-1854-1 | intake-1854#record | [unverified] Review portable manifest and teacher-binding contracts; check architecture/backend support before local model adoption. | knowledge-only → K11 |
| S1-1855-1 | intake-1855#record | [unverified] Review as backend candidate under existing TD-23; verify joint-head execution, batching and calibration before accepting economics. | monitor → M1 |
| S1-1856-1 | intake-1856#record | [unverified] Dive token/logprob integrity and per-cell result provenance. | knowledge-only → K9 |
| S1-1856-2 | intake-1856#record | [unverified] Assess one cross-harness receipt schema using existing UTM pairing keys; preserve verifier failures and capture grades. | primitive-now → P3 |
| S1-1857-1 | intake-1857#record | [unverified] Compare proposed capabilities with existing host-owned menus, freshness gates, abstention and receipts before adding tasks. | knowledge-only → K7 |
| S1-1857-2 | intake-1857#record | [unverified] After dives, design a paired small-backend/27B/baseline replay measuring failures, escalation cost and marginal residency under matched traffic. | monitor → M1 |
| S1-1858-1 | intake-1858#record | [unverified] Compare requirements with current host-owned menus, freshness checks, abstention and decision/memory contracts. | knowledge-only → K7 |
| S1-1859-1 | intake-1859#record | [unverified] Review adapter separation; distinguish teacher fidelity, human-label accuracy and held-out correctness calibration. | knowledge-only → K7 |
| S1-1860-1 | intake-1860#record | [unverified] Verify release-card scores, weight/runtime contract and hosted price at primary sources during selected dive. | monitor → M7 |
| S1-1861-1 | intake-1861#record | [unverified] Retain reporter, suite, cohort and hosted-versus-weights scope; verify load-bearing numbers at primary release artifacts. | monitor → M7 |
| S1-1862-1 | intake-1862#record | [unverified] Compare edition/cohort and denominator contracts with decision receipts; report selective risk/coverage separately from index score. | knowledge-only → K7 |
| S1-1863-1 | intake-1863#record | [unverified] Dive per-primitive calibration, threshold selection and exposure controls for TD-23; prefer frozen replay before broad benchmarking. | knowledge-only → K7 |
| S1-1864-1 | intake-1864#record | [unverified] Review pinned implementation together with docs for a scoped capability adapter. | knowledge-only → K8 |
| S1-1865-1 | intake-1865#record | [unverified] Consider a compact typed-decision backend candidate inside existing TD-23; first verify loader, head semantics, timing scope and calibration. | monitor → M1 |
| S1-1866-1 | intake-1866#record | [unverified] Correct the essay's weights-only generalization; compare model timing, network overhead and realized action latency separately. | knowledge-only → K2 |
| S1-1867-1 | intake-1867#record | [unverified] Review manifest and evaluation-identity patterns; resolve current train/eval budget mismatch before treating scripts as a reproduction recipe. | knowledge-only → K9 |
| S1-1868-1 | intake-1868#record | [unverified] Snapshot scorer edition, benchmark cohort, result provenance and timing scope for every comparison. | knowledge-only → K7 |
| S1-1869-1 | intake-1869#record | [unverified] Dive coherence controls before composing probability-based action rules; consider a reusable label-free probe. | knowledge-only → K7 |
| W1-MONTY-CONTRACT | intake-1850#record; intake-1864#record | Prepare one execution-adapter contract covering explicit capabilities, callback deadlines, total session wall time, output/mount bounds and terminal-error disposal. | knowledge-only → K8 |
| W1-MONTY-STATE | intake-1850#record; intake-1864#record | Specify a distinct authenticated/versioned Monty snapshot envelope and explicit authority reattachment if this backend is selected. | monitor → M2 |
| W1-MONTY-COMPAT | intake-1850#record; intake-1864#record | Inventory existing REPL imports, value types and persistence requirements against Monty's local subset. | knowledge-only → K8 |
| W1-MONTY-PERFORMANCE | intake-1850#record; intake-1864#record | Retain latency numbers with their warm-pool, replay and sampling definitions; defer adoption decisions based on performance. | knowledge-only → K2 |
| W1-MONTY-SECURITY-LINEAGE | intake-1850#record; intake-1864#record | Reconcile historical exploit and fix commits using the independent report and publisher postmortem. | knowledge-only → K2 |
| W1-MH-RECEIPT | intake-1856#record; intake-1867#record | Extend existing cross-harness evidence receipts with actual harness/version, served-checkpoint attestation, provider/capture purpose, effective sampling and budgets, verifier identity and token-accounting scope. | knowledge-only → K9 |
| W1-MH-CAPTURE-CONTRACT | intake-1856#record; intake-1867#record | Represent capture capability, exact engine IDs, authoritative masks and logprob validation as a separate eligibility contract linked to existing UTM pairing keys. | knowledge-only → K9 |
| W1-MH-ATTEMPT-ACCOUNTING | intake-1856#record; intake-1867#record | Preserve verifier outcome independently of telemetry/capture status and retain an append-only attempt history; reuse EvalTower's existing failure dispositions. | primitive-now → P3 |
| W1-MH-EXPOSURE-SELECTION | intake-1856#record; intake-1867#record | Record task-group, rollout, retained-update, supervised-token and processed-token exposure; distinguish validation-selected checkpoints from locked test evaluation. | knowledge-only → K9 |
| W1-MH-EFFICIENCY-OBJECTIVE | intake-1856#record; intake-1867#record | Retain correctness-gated native-tool efficiency shaping as a documented candidate objective, separate from binary router-success labels. | knowledge-only → K6 |
| W1-MH-FULL-TRAINING | intake-1856#record; intake-1867#record | Monitor full multi-harness weight training rather than initiate reproduction. | monitor → M3 |
| W1-joint-head-protocol | intake-1855#record; intake-1859#record; intake-1865#record | [unverified] Add Clef/Flash joint-schema semantics as a separate TD-23 candidate protocol, preserving independent and staged-dependent controls. | monitor → M1 |
| W1-raw-distribution-contract | intake-1855#record; intake-1859#record; intake-1865#record | [unverified] Retain raw probabilities, rounding, invalid mass, backend confidence definition, and caller-computed statistics separately. | knowledge-only → K7 |
| W1-input-loss-and-refusal | intake-1855#record; intake-1859#record; intake-1865#record | [unverified] Record retained-state/input-loss metadata and keep abstention, explicit refusal, invalid output, and transport failure distinct. | knowledge-only → K7 |
| W1-live-menu-authority | intake-1855#record; intake-1859#record; intake-1865#record | [unverified] Route backend selections through existing prepared_action revalidation; host owns live menus, freshness, authority, fallback, and ACT/ABSTAIN/ESCALATE policy. | knowledge-only → K5 |
| W1-resolved-identity | intake-1855#record; intake-1859#record; intake-1865#record | [unverified] Capture requested alias and resolved weight/head/code revision separately; do not accept echoed model names as resolution. | knowledge-only → K7 |
| W1-autotrust-mode-isolation | intake-1855#record; intake-1859#record; intake-1865#record | [unverified] Preserve unmerged decision adapters and explicit base-generation routing; label direct, wide-option, permutation, tournament, and reasoning modes separately. | monitor → M1 |
| W1-gold-calibration-and-ood | intake-1855#record; intake-1859#record; intake-1865#record | [unverified] Separate teacher fidelity from gold correctness; predeclare labelled, source-group-disjoint calibration and OOD/unknown screens. Exclude uniform placeholder relevance labels. | knowledge-only → K7 |
| W1-decision-economics | intake-1855#record; intake-1859#record; intake-1865#record | [unverified] Use total cost per correct eligible decision, including input/schema tokens, failures, retries, escalation, and end-to-end timing; keep inference and network components separate. | primitive-now → P1 |
| W1-hardware-and-modality-boundary | intake-1855#record; intake-1859#record; intake-1865#record | [unverified] Gate local deployment and multimodal adoption on actual released-path compatibility and modality-specific evidence; keep production kernels untouched. | monitor → M8 |
| W1-XLLM-ARTIFACT-BINDING | intake-1853#record; intake-1854#record | [unverified] Preserve teacher-manifest binding and closed-file integrity checks in any future checkpoint adapter; reject or separately validate legacy student .pt files. | knowledge-only → K11 |
| W1-XLLM-CLAIM-SCOPE | intake-1853#record; intake-1854#record | [unverified] Carry prefill-only timing scope, task-specific quality losses, total parameters and finite-depth theorem qualifications into every downstream comparison. | knowledge-only → K11 |
| W1-XLLM-RUNTIME-WATCH | intake-1853#record; intake-1854#record | [unverified] Keep CPU/ROCm/GGUF execution as unproven; scope a port only when an existing handoff relevance trigger is met. | monitor → M5 |
| W1-SDM-FIT-PREDICT-CONTRACT | intake-1852#record | [unverified] Specify context-only recipe fitting, immutable fitted-cache reuse and decision-time feature availability for a future routing adapter. | primitive-now → P4 |
| W1-SDM-CPU-BASELINE | intake-1852#record | [unverified] Prefer a backend-conformance-first CPU tabular comparison before assuming CUDA or relational support; retain the incumbent routing baseline. | monitor → M4 |
| W1-SDM-TABFM-LICENSE | intake-1852#record | [unverified] Keep TabFM asset eligibility separate from SDM Apache licensing and obtain the appropriate license decision before production use. | knowledge-only → K10 |
| W1-SDM-EXPLANATION-CAUTION | intake-1852#record | [unverified] Do not treat gradient attribution as causal or missingness-faithful without checking the reported failure mode. | monitor → M4 |
| W1-typed-per-head-risk-semantics | intake-1863#record; intake-1869#record | [unverified] Separate Choice top-option calibration, Noul event calibration, ordinal Score quality and logical coherence in evaluation/risk receipts. | knowledge-only → K7 |
| W1-typed-heldout-selective-policy | intake-1863#record; intake-1869#record | [unverified] Record per-question threshold-training groups, held-out groups, raw probabilities, tie-aware risk/coverage and clustered intervals. | knowledge-only → K7 |
| W1-typed-coherence-support-ledger | intake-1863#record; intake-1869#record | [unverified] Add an explicit exclusive/exhaustive partition fixture with complement, disjunction, cross-format and bundling checks; log matched support and repeat noise separately. | knowledge-only → K7 |
| W1-index-full-cohort-contract | intake-1862#record; intake-1868#record | [unverified] Preserve edition membership, exclusions, answerable subsets, linked-group completion, failure states, native support and final-index denominators as separate fields. | knowledge-only → K7 |
| W1-index-publication-reconciliation | intake-1862#record; intake-1868#record | [unverified] Reconcile Space formulas and kit weighting, and trace the kit 57.89 versus Space 57.91 Jev artifacts without assuming a scoring bug. | knowledge-only → K7 |
| W1-timing-cohort-risk-receipt | intake-1863#record; intake-1869#record | [unverified] Bind timing to successful/attempted/refused counts, sampled cohort, network/local path, concurrency, warmup, startup exclusions and fast-path parity. | primitive-now → P1 |
| W1-jev-cache-license-boundary | intake-1863#record; intake-1869#record | [unverified] Review released-response permissions before cache reuse beyond research/evaluation; keep MIT analysis code distinct from restricted Jev responses. | knowledge-only → K7 |
| W2-monty-monty-release-attribution | monty | [unverified] Correct patch attribution to PR381/v0.0.17 and retain unknown remote-commit qualification. | knowledge-only → K2 |
| W2-monty-monty-collector-invariant-review | monty | [unverified] Require pin-specific lifetime, reentrancy, traversal and aliasing review; distinguish ordinary tests from Miri-sensitive coverage. | monitor → M2 |
| W2-monty-monty-authority-minimization | monty | [unverified] Keep secrets outside worker authority and explicitly inventory callback/mount permissions; do not equate subprocess isolation with an OS sandbox. | knowledge-only → K8 |
| W2-monty-monty-state-and-lifecycle-boundaries | monty | [unverified] Preserve Wave1 requirements for authenticated snapshots, cumulative host deadlines, terminal-error disposal and import/checkpoint compatibility. | primitive-now → P2 |
| W2-license-SDM-TABFM-LICENSE | license | [unverified] Preserve separate wrapper/asset licenses and compare intended TabFM use against the pinned asset terms before approval. | knowledge-only → K10 |
| W2-license-MONTY-CONTRACT | license | [unverified] Retain explicit capabilities, callback/session deadlines, output/mount bounds and terminal memory/time-error disposal in the execution-adapter contract. | knowledge-only → K8 |
| W2-license-MONTY-STATE | license | [unverified] Require authenticated/versioned snapshot provenance and explicit authority reattachment if Monty resume is adopted. | monitor → M2 |
| W2-license-MONTY-COMPAT | license | [unverified] Preserve the existing import/value/persistence compatibility inventory proposal. | knowledge-only → K8 |
| W2-license-MONTY-PERFORMANCE | license | [unverified] Retain warm-pool, replay and sampling qualifications; do not infer EPYC advantage. | knowledge-only → K2 |
| W2-license-MONTY-SECURITY-LINEAGE | license | [unverified] Preserve the original report's historical exploit/fix reconciliation proposal; this second-reader pass does not resolve it. | knowledge-only → K2 |
| W2-mh-MH-RECEIPT | mh | [unverified] Define an effective-run receipt: source/harness revisions, served checkpoint attestation, provider, capture purpose, sampling, budgets, verifier and token-accounting scope. | knowledge-only → K9 |
| W2-mh-MH-CAPTURE-CONTRACT | mh | [unverified] Specify exact-ID, behavior-logprob and authoritative-mask eligibility separately from generic trace validity. | knowledge-only → K9 |
| W2-mh-MH-ATTEMPT-ACCOUNTING | mh | [unverified] Keep append-only attempts and verifier outcomes separate from telemetry/capture success; reuse existing disposition accounting. | primitive-now → P3 |
| W2-mh-MH-EXPOSURE-SELECTION | mh | [unverified] Audit sampled/retained episodes, rows, supervised/processed tokens, committed updates, checkpoint selection and unseen-harness coverage. | knowledge-only → K9 |
| W2-mh-MH-HISTORICAL-PROVENANCE | mh | [unverified] Bind every published aggregate to experiment family, checkpoint lineage, attempts, cohort membership and source artifacts; separate plotting samples from raw evidence. | knowledge-only → K9 |
| W2-mh-MH-QUALIFICATION-TIERS | mh | [unverified] Distinguish eval compatibility, capture-reader retention, optimizer diagnostic and synchronized reward-normalized training. | monitor → M3 |
| W2-mh-MH-GROUPING-AUDIT | mh | [unverified] Record grouping boundary, zero-advantage fraction, baseline population and retained-gradient exposure; preserve uncertainty about portability. | monitor → M3 |
| W2-mh-MH-EFFICIENCY-OBJECTIVE | mh | [unverified] Keep binary correctness and correctness-conditioned efficiency rewards separate; avoid treating descriptive savings as causal reward benefit. | knowledge-only → K6 |
| W2-mh-MH-FULL-TRAINING | mh | [unverified] Retain full reproduction as a trigger-gated follow-on, not an immediate benchmark or deployment. | monitor → M3 |
| W2-clef-auto-mode-isolation | clef | [unverified] Preserve unmerged adapter/base routing and record direct, wide-option and reasoning modes separately. | knowledge-only → K7 |
| W2-clef-gold-calibration | clef | [unverified] Separate teacher fidelity, fitted-temperature performance and held-out gold correctness before threshold selection. | knowledge-only → K7 |
| W2-clef-runtime-identity | clef | [unverified] Require resolved weight/head/code/configuration identity, or explicitly mark runtime identity unresolved. | knowledge-only → K7 |
| W2-clef-hosted-contract | clef | [unverified] Preserve hosted-specific question/image/context limits and truncation provenance; require a concrete video contract before modality adoption. | knowledge-only → K4 |
| W2-clef-hosted-economics | clef | [unverified] Record inference, round-trip, retry/escalation and total cost separately; evaluate cost per correct eligible decision. | primitive-now → P1 |
| W2-clef-label-provenance | clef | [unverified] Track stream, teacher/gold/programmatic/placeholder status and split/group provenance; quarantine uniform relevance labels. | knowledge-only → K7 |
| W2-clef-order-controls | clef | [unverified] Pair shuffled-order tests with fixed-order repeats, stable tie handling and complete failure denominators. | knowledge-only → K7 |
| W2-clef-dataset-shortcut-controls | clef | [unverified] Carry text-free picker baselines, gold-string leakage and model/domain overlap alongside accuracy. | knowledge-only → K7 |
| W2-clef-strict-client-validation | clef | [unverified] Validate exact keys, finite nonnegative mass, normalization and selected-ID consistency before repair; preserve invalid raw output. | knowledge-only → K7 |
| W2-clef-benchmark-transparency | clef | [unverified] Attach method/addendum, sample manifest, scoring tolerances, support signature, raw-to-aggregate linkage and timing/price basis to cited external results. | knowledge-only → K7 |
| W2-calib-second-reader-anchor-strengthening | calib | [unverified] Parent should apply the stronger anchors above, retaining publisher-description and static-code qualifications. | knowledge-only → K2 |
| W2-calib-retract-truncated-tree-absence | calib | [unverified] Retract the Wave-1 calibration README/scripts-drift finding and record that the complete pinned tree includes the advertised scripts and tests. | knowledge-only → K2 |
| W2-calib-typed-per-head-risk-semantics | calib | [unverified] Keep top-option correctness calibration, Noul event calibration, ordinal Score quality, API confidence and coherence in separate receipt fields. | knowledge-only → K7 |
| W2-calib-cached-evaluation-support-contract | calib | [unverified] Preserve requested, cached, parsed, scored and excluded counts, per head and per linked group; distinguish conditional metrics from full-attempt outcomes. | knowledge-only → K7 |
| W2-calib-typed-heldout-selective-policy | calib | [unverified] Bind per-head thresholds to development groups and retain held-out groups, probability target, tie convention and clustered uncertainty. | knowledge-only → K7 |
| W2-calib-typed-coherence-support-ledger | calib | [unverified] Add explicit partition assumptions, common-support counts, retry/repeat selection and noise assumptions to coherence receipts. | knowledge-only → K7 |
| W2-calib-option-readout-provenance | calib | [unverified] Retain tokenizer/model revisions, option-code mapping, original label mass, thinking mode and requested/resolved identities. | knowledge-only → K7 |
| W2-calib-response-cache-licence-boundary | calib | [unverified] Record separate code/data permissions and resolve database-to-licence mapping before any response reuse beyond inspection. | knowledge-only → K7 |
| W2-calib-bounded-author-log-recomputation | calib | [unverified] Prefer a small, explicitly configured author-log analysis check before any fresh collection or paper-wide recreation. | monitor → M6 |
| W2-calib-preregistration-evidence-boundary | calib | [unverified] Label internal thresholds as author-analysis metadata, not independently verified prospective preregistration. | knowledge-only → K2 |
| W3-jevbench-JB-VERSIONED-PROTOCOL | intake-1885#record | [unverified] Bind every comparison to method, addenda, scorer, adapters, sample manifest and ranking-view revisions. | knowledge-only → K7 |
| W3-jevbench-JB-DENOMINATOR-CONTRACT | intake-1885#record | [unverified] Carry planned, attempted, scorable, valid, calibrated, paired and cost-known counts alongside metrics. | knowledge-only → K7 |
| W3-jevbench-JB-IDENTITY-RAW-LINKAGE | intake-1885#record | [unverified] Require resolved weights/head/code/effective configuration plus raw-output-to-aggregate linkage, or mark the result non-replayable. | knowledge-only → K7 |
| W3-jevbench-JB-VALIDITY-CALIBRATION | intake-1885#record | [unverified] Preserve raw versus normalized distributions, tolerances, strict validity, calibration population and metric convention. | knowledge-only → K7 |
| W3-jevbench-JB-ECONOMICS-SCOPE | intake-1885#record | [unverified] Separate observed billing, reservation, proxy/reference pricing, adjusted latency and setup time; retain total cost per correct eligible decision. | knowledge-only → K7 |
| W3-jevbench-JB-LICENSE-EXPORT | intake-1885#record | [unverified] Reuse licensed evidence/export patterns while enforcing upstream data terms and sealed-data boundaries. | knowledge-only → K7 |
| W3-jevbench-JB-FULL-REPLAY | intake-1885#record | [unverified] Keep full v1.5.6 reproduction conditional on exact public/private artifact access and a concrete project decision. | monitor → M6 |
| W3-tabular-P4-BASELINE-CONFORMANCE | intake-1888#record to intake-1890#record | [unverified] Add effective-config, task-metric, grouping, preprocessing, missingness and estimator/readout checks to any proposed tabular baseline recipe. | knowledge-only → K10 |
| W3-tabular-P4-TABULAR-SCREEN | intake-1888#record to intake-1890#record | [unverified] Keep tabular execution, quality comparison and explanation testing dormant until backend, license and leakage prerequisites pass. | monitor → M4 |
| PEER-jevbench-JB-VERSIONED-PROTOCOL | intake-1885#record | [unverified] Preserve post-result headline amendment and distinguish historical placement rules from current official addendum ranks. | knowledge-only → K7 |
| PEER-jevbench-JB-IDENTITY-RAW-LINKAGE | intake-1885#record | [unverified] Distinguish displayed artifact hashes from independently checked artifacts and execution-attested evaluator revisions. | knowledge-only → K7 |
| PEER-jevbench-order-controls | intake-1885#record | [unverified] Record execution sequence and option-order policy separately from order-independent dataset identity. | knowledge-only → K7 |
| PEER-jevbench-JB-LICENSE-EXPORT | intake-1885#record | [unverified] Keep publication privacy separate from API exposure and operator retention assurances. | knowledge-only → K7 |
| PEER-composite-anchors | intake-1852#record to intake-1853#record/1854/1881 | Parent persists repaired composite spans, exact sampler quote and sufficient-theorem wording. | knowledge-only → K2 |
| PEER-final-label-provenance | Godel independent source/context recheck | [unverified] Preserve stream-specific teacher/provenance and companion placeholder-label qualifications. | knowledge-only → K7 |
| PEER-final-gold-calibration | Godel independent source/context recheck | [unverified] Keep teacher-target matching separate from gold correctness and audited holdout quality. | knowledge-only → K7 |
| PEER-final-order-controls | Godel independent source/context recheck | [unverified] Retain shared-K comparisons, fixed-order controls and complete/incomplete permutation denominators. | knowledge-only → K7 |
| PEER-final-dataset-shortcut-controls | Godel independent source/context recheck | [unverified] Preserve failed G3, eight-versus-six discrepancy, lexical leakage and model/domain overlap. | knowledge-only → K7 |
| PEER-final-strict-client-validation | Godel independent source/context recheck | [unverified] Require exact keys, finite bounded probabilities and explicit normalization semantics. | knowledge-only → K7 |
| PEER-final-runtime-identity | Godel independent source/context recheck | [unverified] Distinguish requested aliases/source pins from resolved runtime artifact attestations. | knowledge-only → K7 |
| PEER-final-paid-call-budget-semantics | Godel independent source/context recheck | [unverified] Label projected spend screening as estimate-based; preserve unknown usage and potentially billed retries. | knowledge-only → K4 |
| PEER-final-benchmark-transparency | Godel independent source/context recheck | [unverified] Bind claims to method amendments, evaluator provenance, ranking view, coverage and separate data licenses. | knowledge-only → K7 |
| PEER-final-hosted-economics | Godel independent source/context recheck | [unverified] Separate observed billing, reference-price estimates, proxy usage and latency adjustments. | knowledge-only → K7 |
| PEER-final-MONTY-CONTRACT | Godel independent source/context recheck | [unverified] Retain Round 2 outcome qualifications and the changed Round 3 server/mount boundary. | knowledge-only → K8 |
| PEER-final-P4-BASELINE-CONFORMANCE | Godel independent source/context recheck | [unverified] Preserve effective-config, metric, grouping, preprocessing, missingness and estimator/readout checks. | knowledge-only → K10 |
| PEER-final-P4-TABULAR-SCREEN | Godel independent source/context recheck | [unverified] Keep quality, portability and explanation execution dormant until backend, license, leakage and authorization prerequisites pass. | monitor → M4 |
| W3-publication-BH-VERSIONED-PUBLICATION | intake-1898#record | [unverified] Record committed/API hash equality separately from displayed scorer-output hashes and private raw-run correctness. | knowledge-only → K7 |
| W3-publication-BH-EXPOSURE-IDENTITY | intake-1899#record | [unverified] Preserve exposure, self-reported base identity, private raw linkage and unknown pre-run public-code availability as distinct fields. | knowledge-only → K7 |
| W3-context-wave3-confidence-targets | intake-1891#record to intake-1892#record/1893/1894/1895 | [unverified] Identify the probability/confidence target of every ECE, selective-risk and mean-confidence field. | knowledge-only → K7 |
| W3-context-wave3-common-support-and-ties | intake-1891#record to intake-1892#record/1893/1894/1895 | [unverified] Preserve requested, successful-common, confidence-masked and comparable-pair support separately; expose zero-support and tie-cut outcomes. | knowledge-only → K7 |
| W3-context-wave3-collection-provenance | intake-1891#record to intake-1892#record/1893/1894/1895 | [unverified] Separate final-attempt HTTP elapsed time from parsed-answer and retry-inclusive time; retain requested/response aliases without treating them as immutable weight identity. | primitive-now → P3 |
| W3-context-wave3-optimistic-hand-off | intake-1891#record to intake-1892#record/1893/1894/1895 | [unverified] Label same-item threshold selection descriptive, not held-out certification. | knowledge-only → K7 |
| W3-context-wave3-vendor-page-drift | intake-1891#record to intake-1892#record/1893/1894/1895 | [unverified] Attribute the historical negation quotation to the pinned harness unless historical vendor publication is independently recovered. | knowledge-only → K3 |
| W3-capture-SFT-exposure-and-denominator-qualification | intake-1887#record/intake-1896#record | [unverified] Refine P3 manifests with per-recipe task/example/update budgets, checkpoint selection, exposure/overlap identities and complete evaluation coverage. | knowledge-only → K9 |
| W3-capture-TRL-exact-token-and-group-consumer-contract | intake-1887#record/intake-1896#record | [unverified] Refine P3 capture qualification with exact IDs/logprobs/labels/masks, callback ordering, group identity, preparation pins and truncation/drop accounting. | knowledge-only → K9 |
| W3-capture-TRL-unscorable-normalization-accounting | intake-1887#record/intake-1896#record | [unverified] Refine P3 accounting to distinguish task failure, infrastructure failure, missing reward, zero advantage and token-loss normalization membership. | knowledge-only → K9 |
| P4-close-SDM-FIT-PREDICT-CONTRACT | intake-1852#record/intake-1881#record | [unverified] Implement the shared typed availability and immutable fitted-artifact contract. | primitive-now → P4 |
| P4-close-SDM-TABFM-LICENSE | intake-1852#record/intake-1881#record | [unverified] Bind separate asset terms to exact intended-use eligibility. | knowledge-only → K10 |
| P4-close-SDM-CPU-BASELINE | intake-1852#record/intake-1881#record | [unverified] Retain the bounded CPU-first comparison as a monitor. | monitor → M4 |
| P4-close-SDM-EXPLANATION-CAUTION | intake-1852#record/intake-1881#record | [unverified] Retain gradient sensitivity versus causal explanation qualification. | monitor → M4 |

## Source inventory

Inventory references discuss records only; factual warrants remain their primary anchors and corrections. The five provisional entries cannot supply an empirical or mechanism premise.

| Record | Source | Verification | Locator |
|---|---|---|---|
| intake-1850#record | Monty — capability-mediated Python sandbox and persistent worker sessions | dive-verified | [Primary source](https://pydantic.dev/docs/monty/get-started/) |
| intake-1851#record | Frameworks Are More Important in the AI Era, Not Less | stage1-unverified | [Primary source](https://fluin.io/blog/frameworks-in-the-ai-era) |
| intake-1852#record | Structured Data Models — unified tabular and relational model/tensor/preprocessing library | dive-verified | [Primary source](https://github.com/NVIDIA/structured-data-models) |
| intake-1853#record | Towards Looped Models Done Right. Part II: Rethinking at Fixed Points | dive-verified | [Primary source](https://github.com/ifm-ai/xllm-loop/blob/3af99f493e14fba162625d5dd687abea551a299e/papers/part2.pdf) |
| intake-1854#record | xLLM-Loop — official looped-model training, native artifacts and prefill-student release | dive-verified | [Primary source](https://github.com/ifm-ai/xllm-loop) |
| intake-1855#record | Clef — 27B multimodal joint-schema decision model | dive-verified | [Primary source](https://huggingface.co/Cloudflare/clef) |
| intake-1856#record | The ultimate guide to multi-harness RL | dive-verified | [Primary source](https://huggingface.co/spaces/FineEnvs/multi-harness-rl) |
| intake-1857#record | System 1 Should Not Be a 27B Model on the Hot Path — operator-supplied technical essay | stage1-unverified | Operator supplied inline text |
| intake-1858#record | OrcaRouter X post — open decision models and System 1 requirements | stage1-unverified | [Primary source](https://x.com/OrcaRouter/status/2106237912610439622) |
| intake-1859#record | autotrust/JEV-27B: fast, calibrated decisions and full reasoning from one open model | dive-verified | [Primary source](https://huggingface.co/blog/autotrust/autotrustjev-27b-fast-calibrated-decisions-and-ful) |
| intake-1860#record | TeksEdge X post — Perplexity open-sourced a 27B decision model | stage1-unverified | [Primary source](https://x.com/TeksEdge/status/2106232780736631103) |
| intake-1861#record | Decision models after Jev: who shipped what, and how to read the claims | stage1-unverified | [Primary source](https://canberk.me/blog/decision-models-after-jev-who-shipped-what/) |
| intake-1862#record | Decision Index — frozen typed-decision suite reproduction and scoring kit | dive-verified | [Primary source](https://github.com/apolinario/decision-index) |
| intake-1863#record | Evaluating and Benchmarking the System One Model Jev | dive-verified | [Primary source](https://arxiv.org/abs/2609.37647) |
| intake-1864#record | Monty — official Rust interpreter, bindings and sandbox runtime | dive-verified | [Primary source](https://github.com/pydantic/monty) |
| intake-1865#record | Clef-Flash — 9B multimodal typed-decision model | dive-verified | [Primary source](https://huggingface.co/Cloudflare/clef-flash) |
| intake-1866#record | Introducing Clef: our open-source decision models, and new RL fine-tuning platform | dive-verified | [Primary source](https://blog.cloudflare.com/clef-decision-models/) |
| intake-1867#record | FineEnvs — multi-harness RL training, task manifests and per-pair evaluation | dive-verified | [Primary source](https://github.com/adithya-s-k/FineEnvs) |
| intake-1868#record | Jev Decision Index — community leaderboard and versioned result bundle | dive-verified | [Primary source](https://huggingface.co/spaces/multimodalart/jev-decision-index) |
| intake-1869#record | Beyond Calibration: Do a Typed-Decision Model's Probabilities Obey the Probability Axioms? | dive-verified | [Primary source](https://arxiv.org/abs/2609.33209) |
| intake-1870#record | Pwning Pydantic's Monty: A $5K Sandbox Escape | dive-verified | [Primary source](https://verialabs.com/blog/pwning-pydantic-monty/) |
| intake-1871#record | Hack Monty - Postmortem | dive-overturned | [Primary source](https://pydantic.dev/articles/hack-monty-postmortem) |
| intake-1872#record | SmolDataEnv RL | dive-verified | [Primary source](https://huggingface.co/spaces/FineEnvs/data-agent-training-comparison-trackio) |
| intake-1873#record | OpenEnv capture/export/qualification slice | dive-verified | [Primary source](https://github.com/huggingface/OpenEnv) |
| intake-1874#record | What Does Multi-Harness RL Learn? Credit Assignment and Portability in Coding Agents | dive-verified | [Primary source](https://arxiv.org/abs/2609.04518) |
| intake-1875#record | autotrust/JEV-27B | dive-verified | [Primary source](https://huggingface.co/autotrust/JEV-27B) |
| intake-1876#record | clef — Cloudflare Workers AI model documentation | dive-verified | [Primary source](https://developers.cloudflare.com/workers-ai/models/clef/) |
| intake-1877#record | clef-flash — Cloudflare Workers AI model documentation | dive-verified | [Primary source](https://developers.cloudflare.com/workers-ai/models/clef-flash/) |
| intake-1878#record | Jev Distill Corpus v3 | dive-verified | [Primary source](https://huggingface.co/datasets/SargeDev/jev-distill-corpus-v3) |
| intake-1879#record | Decision Models Under Pressure | dive-verified | [Primary source](https://github.com/gazelle93/decision-models-under-pressure) |
| intake-1880#record | Clef — JevBench by Benchmark Heaven | dive-verified | [Primary source](https://www.benchmarkheaven.com/jev-models/clef) |
| intake-1881#record | TabFM Non-Commercial License v1.0 | dive-verified | [Primary source](https://huggingface.co/google/tabfm-1.0.0-pytorch) |
| intake-1882#record | Evaluating and Benchmarking the System One Model Jev — companion implementation | dive-verified | [Primary source](https://github.com/AppliedMachineLearning-Lab/jev-benchmarking) |
| intake-1883#record | Beyond Calibration — released stimuli, logs and analysis | dive-verified | [Primary source](https://github.com/bro789/typed-decision-coherence) |
| intake-1884#record | Evaluating and Benchmarking the System One Model Jev — response dataset | dive-verified | [Primary source](https://zenodo.org/records/23039006) |
| intake-1885#record | JevBench | dive-verified | [Primary source](https://github.com/fstandhartinger/jevbench) |
| intake-1886#record | Hack Monty Round 3 & Round 2 results | dive-verified | [Primary source](https://pydantic.dev/articles/hack-monty-3) |
| intake-1887#record | TRL targeted capture, masks and packing consumer | dive-verified | [Primary source](https://github.com/huggingface/trl) |
| intake-1888#record | TabICLv2 replication (classifier only) | dive-verified | [Primary source](https://huggingface.co/ayushkaushal4/tabiclv2-replication) |
| intake-1889#record | GradientExplainer misattributes missing values | dive-verified | [Primary source](https://github.com/NVIDIA/structured-data-models/issues/947) |
| intake-1890#record | TabFM contra CatBoost, XGBoost e LightGBM em 10 datasets tabulares | dive-verified | [Primary source](https://gomesfellipe.github.io/post/2026-08-06-tabfm-vs-gbm/) |
| intake-1891#record | Jevify | dive-verified | [Primary source](https://github.com/uspraveen/Jevify) |
| intake-1892#record | jev-orderby-bench | dive-verified | [Primary source](https://github.com/yodablocks/jev-orderby-bench) |
| intake-1893#record | Jevals benchmark data | dive-verified | [Primary source](https://github.com/Jevals/jevals-data) |
| intake-1894#record | How Jevals scores a decision | dive-verified | [Primary source](https://jevals.com/methodology/) |
| intake-1895#record | Jev 1.13 jaggedness | dive-verified | [Primary source](https://docs.typesafe.ai/model-jaggedness/jev-1.13) |
| intake-1896#record | SmolDataEnv SFT | dive-verified | [Primary source](https://huggingface.co/spaces/FineEnvs/data-agent-sft-trackio) |
| intake-1897#record | About & data sources | dive-verified | [Primary source](https://www.benchmarkheaven.com/about) |
| intake-1898#record | JevBench v1.5.6 — official Jev alternatives ranking | dive-verified | [Primary source](https://www.benchmarkheaven.com/jev-models/v1.5.6) |
| intake-1899#record | Benchmark Heaven (formerly Model Market Comparison) | dive-verified | [Primary source](https://github.com/fstandhartinger/model-market-comparison) |


## Validation and review boundary

Repository grounding used four parallel context-specific readers, followed by main-agent source checks of the identified code paths. The API version and kernel-store links were inspected read-only; no model generation, training, install, reload, production-kernel change or new external research occurred. GitNexus root status was current; intake-reader upstream impact was LOW (one CLI caller). The plan edit changes no executable interface.

Revision checks passed: all 137 unique mapping IDs and retained recommendations preserved, including 24 Stage 1 rows; all 50 inventory rows unchanged; five steering rows; five new task lines and two existing-task refinements. Intake validation passed (1895 entries), handoff-index validation reported zero problems, record-scoped citation checks passed, and git diff --check passed. An independent final reader passed the narrow scope and code-grounding review. No empirical performance gain or deployment claim is made.

At Stage 4 re-resolve actual task text and owner status against then-current main; preserve freezes and concurrent work. Apply only the reviewed filing scope, validate exact dispositions/indices/citations, and checkpoint scoped changes. Never merge this review artifact as if it were an implementation patch.
