# Research-intake Stage-3 plan — harness and inference sources (2026-11-06)

**Run**: intake-2650..intake-2661 · **Lane**: `intake/20261106-harness-inference` @ `ec6aba4b17` · **Sources**: t3code, Foundry Local, HarnessMM + 9 expansion entries.

**Posture**. The batch's common finding is that harness-level savings are easy to over-attribute: HarnessMM's headline is 64-88% context shrink rather than callback removal; ActionEngine's 3.2x is one hosted-API mean; HARBOR ties the manual peak inside a corrected noise floor; CORTEX's reuse buys fewer rule evaluations and slower medians; vCache's bound is on the cache, not the skip. So the plan spends its immediate work on **soundness and measurement contracts**, and gates every inference-spending experiment behind a fired trigger.

## Work packets

| Packet | Action | Owner |
|---|---|---|
| P1 | Dispatch-time tool epoch and evidence class | handoffs/active/harness-program.md |
| P2 | Cross-session handoff contract | handoffs/active/context-and-token-economy.md |
| P3 | Harness reuse economics and attribution | handoffs/active/harness-program.md |
| P4 | Host and model variant descriptors | handoffs/active/routing-program.md |
| P5 | Session-bus durability | handoffs/active/coordination-and-churn-pipeline.md |
| K1 | Evidence standards retained as knowledge | handoffs/active/harness-program.md |
| M1 | Inference-gated measurements (durable triggers) | handoffs/active/harness-program.md |

**P1** is the only packet that touches execution semantics: three additive fields and one fingerprint extension, no inference. **P2/P5** are contracts over existing files. **P3** is reporting discipline. **P4** is schema-only: no selector ships until the descriptor and host manifest exist (M-5).

## Proposed task lines

- [ ] **UFH-TE-1 — Add validator identity and a conclusion validity interval to the decision receipt.** Extend `decision_receipt.v1` with `validator_id`, `validator_version` and `conclusion_valid_until_ns` (all optional, default None; no behaviour change). Acceptance: the schema and the producer emit the fields; an existing receipt without them still validates; no gate changes.

- [ ] **UFH-TE-2 — Fold serving identity into the dispatch-time prepared-action recheck.** Extend the dispatch fingerprint with descriptor digest, handler artifact and config digest, serving process start time and serving tree commit. A mismatch returns `stale` and routes to re-form; stored calls are never executed silently. Acceptance: a synthetic handler swap between formation and dispatch produces `stale`, a benign restart does not, and a regression test pins both.

- [ ] **UFH-TE-3 — Declare admissible evidence classes for any skipped or reused call.** Write the rule that a 'safely skipped' or 'reused' claim names one of: identity receipt (the call was executed with a bound receipt), rate-tau audited population (a fraction of skips are recomputed and scored), or none. Forbid statistical language without an audited denominator. Acceptance: the rule is in the receipt contract and a lint check flags any handoff sentence that claims a skip without a class.

- [ ] **CTX-HO-1 — Amend CF-AB-1 A6 to the measured handoff field set and co-metric.** Replace A6's three-field schema with the seven deterministic fields (repository change state, changed source files, non-source artifacts, validation outcome, latest validation command, latest validation evidence, continuation-state label) and seven model-filled fields; add `events per solved task` beside uncached prefill as a co-metric. Acceptance: A6 text carries both field lists and both metrics; no new arm.

- [ ] **CTX-HO-2 — Add a typed handoff-transfer record and ledger to the session bus.** Add a `handoff-transfer` message kind and a coordinator-owned append-only `transfers/` ledger with transfer_id, source point, base point, coverage, selected and omitted ids, budget_bytes, status, consumer, consumed_at; lazy resolution on first dispatch; ack deduped on transfer_id. Acceptance: schema, single-writer rule and a two-main fixture test.

- [ ] **CTX-HO-3 — Render validation evidence into the /log checkpoint envelope.** The completed-checkpoint envelope carries a `resume_state` block with the latest validation command, its observed output or exit, remaining uncertainty, a rollback note, non-source artifacts and a continuation-state label. Acceptance: a real checkpoint renders a populated block from the executed `--validation-json`; missing evidence renders as explicitly unknown.

- [ ] **HIL-RE-1 — Require a call-count decomposition on every token-saving claim.** Any harness token-saving figure we cite or produce must state delta calls (certified bypasses vs other), tokens/call before and after, and whether the effect is prefill or decode. A saving that cannot be decomposed this way may not be described as callback elimination. Acceptance: the reporting convention text and one worked example from intake-2652.

- [ ] **HIL-RE-2 — Register non-prompt reuse substrates with their invalidation sets.** One knowledge row naming per-operation graph reuse, per-action decision-graph reuse and prefix-cache reuse as distinct mechanisms, each with what invalidates it. Acceptance: the row exists and no existing reuse task is duplicated.

- [ ] **HIL-RE-3 — Add a telemetry read/write-asymmetry invariant for harness flags.** When a flag fires on the write side but its consumer counter is identically zero, mark it silent, exclude it from any sweep and emit one typed event. Acceptance: a synthetic unwired consumer trips the check; a clean run is silent; no inference.

- [ ] **HIL-RE-4 — Add an authoring-cost column to the S4 reporting contract.** Any reuse-bearing harness feature reports one-time authoring cost in dollars and engineer-hours, the break-even N against the paired baseline, whether that N is per-artefact or cross-artefact, and build cost separately from steady state. Acceptance: the S4 contract text carries the four fields.

- [ ] **RTG-VAR-1 — Emit a host-capability manifest as a compiled input.** Add `orchestration/host_capabilities.yaml` (CPU flags, NUMA nodes, GPU arch and VRAM, ROCm version, RAM) probed from the existing inventory scripts and consumed by the registry compiler. Acceptance: the manifest is generated reproducibly and a golden test pins its shape.

- [ ] **RTG-VAR-2 — Add a variant dimension to the model descriptor.** Extend the descriptor with `variants: [{quant, backend, device, path, sha256, ctx_max, measured_tps, quality_ref}]`, seeded from existing role entries and normalising the free-form quant strings. Acceptance: schema plus a migration that resolves all existing roles to at least one variant with no invented measurement.

- [ ] **BUS-ID-1 — Refuse duplicate message ids in session_bus append.** `cmd_append` exits non-zero when a caller-supplied id already exists in the destination, instead of trusting it; add a regression test. Acceptance: a second append with the same explicit id fails and leaves one row.

- [ ] **BUS-ID-2 — Record the unbounded-dedup invariant in BUS_PROTOCOL.** State that messages never expire, retention is cursor-gated, `--stale-after-h` labels but never drops, and a time-bounded TTL must not be introduced. Acceptance: the invariant appears with the rule number and the code references.

- [ ] **BUS-ID-3 — Re-screen the R6c post-reboot brief against current rebuild_state.** Check whether rebuild now derives tokens, heartbeat task_id, leases and checkpoint fields; if so, narrow or close R6c. Acceptance: a dated screening note, not a new task.

## Complete recommendation mapping

| Ledger row | Source or review | Retained recommendation | Terminal plan mapping |
|---|---|---|---|
| RI-11 | intake-2650#4 | Amend CF-AB-1 A6 to the measured field set and add an events co-metric | P2 / CTX-HO-1 |
| RI-12 | intake-2650#3 | Add a typed handoff-transfer record and ledger to the session bus | P2 / CTX-HO-2 |
| RI-13 | intake-2653#1 | Render validation evidence into the /log checkpoint envelope | P2 / CTX-HO-3 |
| RI-14 | intake-2653#2 | Add events-per-solved-task as an A6 co-metric | P2 / CTX-HO-1 |
| RI-15 | intake-2658#0 | Fold serving identity into the dispatch-time prepared-action recheck | P1 / UFH-TE-2 |
| RI-16 | intake-2658#1 | Constrain any omission certificate to three added fields and exact-pin the default | P1 / UFH-TE-3 |
| RI-17 | intake-2660#0 | Add validator identity and a conclusion validity interval to the receipt | P1 / UFH-TE-1 |
| RI-18 | intake-2657#2 | Declare admissible evidence classes for any skipped or reused call | P1 / UFH-TE-3 |
| RI-19 | intake-2661#3 | Refuse statistical language for a skip without an audited denominator | P1 / UFH-TE-3 |
| RI-20 | intake-2652#1 | Require a call-count decomposition on every token-saving claim | P3 / HIL-RE-1 |
| RI-21 | intake-2656#2 | Add an authoring-cost column to the S4 reporting contract | P3 / HIL-RE-4 |
| RI-22 | intake-2651#2 | Emit a host-capability manifest as a compiled input | P4 / RTG-VAR-1 |
| RI-23 | intake-2651#3 | Add a variant dimension to the model descriptor | P4 / RTG-VAR-2 |
| RI-24 | intake-2655#i | Refuse duplicate message ids in session_bus append | P5 / BUS-ID-1 |
| RI-25 | intake-2655#iii | Record the unbounded-dedup invariant in BUS_PROTOCOL | P5 / BUS-ID-2 |
| RI-26 | intake-2654#3 | Borrow the nightly capability-diff pattern for pin audits | K1 / knowledge-only |
| RI-27 | intake-2652#2 | Register non-prompt reuse substrates with invalidation sets | P3 / HIL-RE-2 |
| RI-28 | intake-2659#2 | Add a telemetry read/write-asymmetry invariant | P3 / HIL-RE-3 |
| RI-29 | intake-2653#3 | Re-screen the R6c post-reboot brief against rebuild_state | P5 / BUS-ID-3 |
| RI-30 | intake-2658#0 | Exact-pin stored and replayed calls by default; record the re-formation cost | K1 / knowledge-only |
| RI-01 | intake-2650#record | Port T3's SQL event store, projections, command receipts and outbox into EPYC | decline: Bus rule 1 (single writer per file) and rule 9 (rebuildable from files) are incompatible with a central store; T3's own recovery is a read-only copy of userdata with no export API. Kept as design reading only. |
| RI-02 | intake-2651#record | Port Foundry's first-use download and content-addressed cache | decline: EPYC's 162 model paths are pre-staged locally with sha256 pinned; a downloader solves a problem we do not have (dive port-cost estimate: +3-5 days for zero benefit). |
| RI-03 | intake-2651#record | Treat Foundry Local as a serving runtime candidate | decline: ONNX-only, no ROCm EP shipped, single-user with no batching; the MI210 path would require model conversion plus a quality-parity study, for a runtime that cannot serve our workload. |
| RI-04 | intake-2652#record | Reproduce the HumanEval and MBPP arms | decline: Hosted harnesses, a self-hosted Qwen3.5-4B actor, no time axis; nothing transfers that the wall-clock probe does not already answer. |
| RI-05 | intake-2659#record | Build a Bayesian harness-flag search | decline: The paper's own pick ties the manual peak within a corrected +/-5.9-pass interval, has no random/grid control, and is warm-started from the manual log; cost is 35-98% of a week's quota. EPYC's flag space is ~10-20 dims where random/OAT is the correct baseline. |
| RI-06 | intake-2660#record | Adopt CORTEX's experience graph, decisive predicates, proof trace or four-mode controller for dispatch | decline: EPYC re-dispatches rather than reuses, so replay warrants buy nothing; the paper's own cost is higher warm latency and +24-30% reasoning work for zero label gain. Two fields are retained instead (validator identity, conclusion validity). |
| RI-07 | intake-2658#record | Port the reviewed effect-profile pipeline, registrar and admission plane | decline: Soundness rests on a reviewed profile premise and a call-site classifier our tool surface cannot support; single-host harness with no registry. Keep the ordering rule and the three-field epoch binding only. |
| RI-08 | intake-2661#record | Build a semantic answer cache with an error bound | decline: Our reuse is exact (prefix cache, ~99% of prompt tokens), which satisfies correctness trivially; a semantic cache adds a quality risk and a calibration burden for throughput we do not need. Revisit only if an approximate reuse tier is proposed AND a rate-tau audit is affordable. |
| RI-09 | intake-2654#record | Consume the ACP registry as a runtime trust source | decline: The registry is an agent catalog with no capability fields in the published index, quarantine is invisible to clients, and 7 of 22 binary manifests ship no sha256. It removes no EPYC work because ACP is a north-facing editor protocol and our injection point is south-facing; pin-source discipline and the capability-diff pattern are borrowed instead. |
| RI-10 | intake-2654#record | Treat ecosystem growth as evidence for or against the ACP verdict | decline: The verdict is layer-based (north vs south), not adoption-based; agent counts do not move it. |
| M-1 | intake-2653#5 | Paired EPYC handoff-debt measurement: repository-only vs rendered note, n>=10 checkpoints, calls and cold-prefill seconds | M1 |
| M-2 | intake-2652#5 | 60-pair ABBA wall-clock probe of literal-action reuse with the six controls | M1 |
| M-3 | intake-2657#5 | Non-LLM share of a tool turn (futility gate) and an idempotence census of the top tools | M1 |
| M-4 | intake-2650#6 | Session-identity capability column (can_resume/fork/rollback/max_context) before any native transfer | M1 |
| M-5 | intake-2651#5 | Variant selector implementation only after the descriptor and host manifest exist | M1 |

## Terminal dispositions

- **Immediate**: all `P1`-`P5` tasks above. Zero-inference except none; no measurement is immediate.
- **Knowledge-only (`K1`)**: registry posture (RI-26), exact-pin default (RI-30), negative precedents from 2652/2659/2660/2661 recorded in the entries.
- **Monitor (`M1`)**, all inference-gated with no active checkbox: handoff-debt measurement, 60-pair wall-clock probe, tool-turn futility gate + idempotence census, session-identity column, variant selector.
- **Declines**: RI-01..RI-10, each with a grounded reason in the payload. No decline rests on platform or missing-software grounds.

## Intake-entry updates

All 12 entries are `dive-verified` with read depth recorded (2650 FULL, 2651 FULL, 2652 FULL, 2653 FULL, 2654 PARTIAL, 2655 PARTIAL, 2656 FULL, 2657 FULL, 2658 FULL, 2659 FULL, 2660 FULL, 2661 FULL). 2651 and 2654 are `knowledge_only`; the rest are `integrated` into the packets above.

## Steering reconciliation

- seq 1 (stage 1): all recommended dives accepted for four waves — `planned`, ref `P1`; executed as authorised.

## Stage-3 filing payload

```json
{
 "format_version": 2,
 "entry_updates": [
  {
   "id": "intake-2650",
   "integration_disposition": "integrated",
   "handoffs_updated": [
    "handoffs/active/context-and-token-economy.md",
    "handoffs/active/coordination-and-churn-pipeline.md"
   ],
   "handoffs_created": [],
   "disposition_evidence": [
    "Stage-3 plan research/intake-stage3-plan-2026-11-06-harness-inference.md maps this entry's dive ledger to a packet, a trigger or an explicit decline."
   ]
  },
  {
   "id": "intake-2651",
   "integration_disposition": "knowledge_only",
   "handoffs_updated": [
    "handoffs/active/routing-program.md"
   ],
   "handoffs_created": [],
   "disposition_evidence": [
    "Stage-3 plan research/intake-stage3-plan-2026-11-06-harness-inference.md maps this entry's dive ledger to a packet, a trigger or an explicit decline."
   ]
  },
  {
   "id": "intake-2652",
   "integration_disposition": "integrated",
   "handoffs_updated": [
    "handoffs/active/harness-program.md"
   ],
   "handoffs_created": [],
   "disposition_evidence": [
    "Stage-3 plan research/intake-stage3-plan-2026-11-06-harness-inference.md maps this entry's dive ledger to a packet, a trigger or an explicit decline."
   ]
  },
  {
   "id": "intake-2653",
   "integration_disposition": "integrated",
   "handoffs_updated": [
    "handoffs/active/context-and-token-economy.md",
    "handoffs/active/coordination-and-churn-pipeline.md"
   ],
   "handoffs_created": [],
   "disposition_evidence": [
    "Stage-3 plan research/intake-stage3-plan-2026-11-06-harness-inference.md maps this entry's dive ledger to a packet, a trigger or an explicit decline."
   ]
  },
  {
   "id": "intake-2654",
   "integration_disposition": "knowledge_only",
   "handoffs_updated": [
    "handoffs/active/harness-program.md"
   ],
   "handoffs_created": [],
   "disposition_evidence": [
    "Stage-3 plan research/intake-stage3-plan-2026-11-06-harness-inference.md maps this entry's dive ledger to a packet, a trigger or an explicit decline."
   ]
  },
  {
   "id": "intake-2655",
   "integration_disposition": "integrated",
   "handoffs_updated": [
    "handoffs/active/coordination-and-churn-pipeline.md"
   ],
   "handoffs_created": [],
   "disposition_evidence": [
    "Stage-3 plan research/intake-stage3-plan-2026-11-06-harness-inference.md maps this entry's dive ledger to a packet, a trigger or an explicit decline."
   ]
  },
  {
   "id": "intake-2656",
   "integration_disposition": "integrated",
   "handoffs_updated": [
    "handoffs/active/harness-program.md"
   ],
   "handoffs_created": [],
   "disposition_evidence": [
    "Stage-3 plan research/intake-stage3-plan-2026-11-06-harness-inference.md maps this entry's dive ledger to a packet, a trigger or an explicit decline."
   ]
  },
  {
   "id": "intake-2657",
   "integration_disposition": "integrated",
   "handoffs_updated": [
    "handoffs/active/harness-program.md"
   ],
   "handoffs_created": [],
   "disposition_evidence": [
    "Stage-3 plan research/intake-stage3-plan-2026-11-06-harness-inference.md maps this entry's dive ledger to a packet, a trigger or an explicit decline."
   ]
  },
  {
   "id": "intake-2658",
   "integration_disposition": "integrated",
   "handoffs_updated": [
    "handoffs/active/harness-program.md"
   ],
   "handoffs_created": [],
   "disposition_evidence": [
    "Stage-3 plan research/intake-stage3-plan-2026-11-06-harness-inference.md maps this entry's dive ledger to a packet, a trigger or an explicit decline."
   ]
  },
  {
   "id": "intake-2659",
   "integration_disposition": "integrated",
   "handoffs_updated": [
    "handoffs/active/harness-program.md"
   ],
   "handoffs_created": [],
   "disposition_evidence": [
    "Stage-3 plan research/intake-stage3-plan-2026-11-06-harness-inference.md maps this entry's dive ledger to a packet, a trigger or an explicit decline."
   ]
  },
  {
   "id": "intake-2660",
   "integration_disposition": "integrated",
   "handoffs_updated": [
    "handoffs/active/harness-program.md"
   ],
   "handoffs_created": [],
   "disposition_evidence": [
    "Stage-3 plan research/intake-stage3-plan-2026-11-06-harness-inference.md maps this entry's dive ledger to a packet, a trigger or an explicit decline."
   ]
  },
  {
   "id": "intake-2661",
   "integration_disposition": "integrated",
   "handoffs_updated": [
    "handoffs/active/harness-program.md"
   ],
   "handoffs_created": [],
   "disposition_evidence": [
    "Stage-3 plan research/intake-stage3-plan-2026-11-06-harness-inference.md maps this entry's dive ledger to a packet, a trigger or an explicit decline."
   ]
  }
 ],
 "opportunity_reviews": {
  "P1": {
   "project_objective": "Store and execute tool calls without a schema-valid call silently changing effect",
   "implementation_ref": "src/typed_decisions/prepared_action.py:47-150 at lane ec6aba4b1",
   "gap": "the dispatch fingerprint covers catalog and read-set hashes but not the handler/interpreter that will execute the call",
   "operational_change": "add serving identity to the fingerprint and validator identity to the receipt",
   "benefit_direction": "fewer silent wrong-effect dispatches; no increase in benign re-formations",
   "owner": "handoffs/active/harness-program.md",
   "execution_conditions": "implementation is permitted immediately; no inference or activation gate",
   "closure_basis": "Immediate schema and guard only; a measured mismatch rate is a separate trigger"
  },
  "P2": {
   "project_objective": "Make cross-session handoff a declared artifact rather than prose",
   "implementation_ref": "context-and-token-economy.md:117 (A6) and coordination/session-bus/BUS_PROTOCOL.md at ec6aba4b1",
   "gap": "A6 carries three fields and the bus has no context-transfer kind or ledger",
   "operational_change": "measured field set, transfer ledger, rendered validation evidence",
   "benefit_direction": "fewer rediscovery turns per takeover; measurable events per solved task",
   "owner": "handoffs/active/context-and-token-economy.md",
   "execution_conditions": "contract and docs immediately; the paired measurement is trigger-gated",
   "closure_basis": "Immediate contract; measurement remains a durable trigger"
  },
  "P3": {
   "project_objective": "Price harness reuse on wall-clock and attribute savings correctly",
   "implementation_ref": "handoffs/active/harness-program.md:417 and :2447 at lane ec6aba4b1",
   "gap": "no claim grammar, no authoring-cost column, no flag-liveness invariant",
   "operational_change": "reporting and instrumentation rules",
   "benefit_direction": "prevents over-attribution; surfaces silent flags",
   "owner": "handoffs/active/harness-program.md",
   "execution_conditions": "doc and invariant immediately; probes are trigger-gated",
   "closure_basis": "Immediate reporting rules; probes remain triggers"
  },
  "P4": {
   "project_objective": "Represent host capability and per-device model variants as data",
   "implementation_ref": "master-model-registry.yaml and stack_topology.yaml at lane ec6aba4b1",
   "gap": "one model per role, no variant dimension, host facts hardcoded",
   "operational_change": "host manifest plus variant schema",
   "benefit_direction": "selectable per-device variants without hardcoded env blocks; no throughput claim until measured",
   "owner": "handoffs/active/routing-program.md",
   "execution_conditions": "data and schema only; selector implementation is a later trigger",
   "closure_basis": "Immediate schema; selection gated"
  },
  "P5": {
   "project_objective": "Keep the bus recoverable and lossless",
   "implementation_ref": "scripts/coordination/session_bus.py:1607-1611 and BUS_PROTOCOL.md:30-33,85-91 at lane ec6aba4b1",
   "gap": "append trusts a caller-supplied id; the unbounded-dedup property is implicit",
   "operational_change": "reject duplicate ids; document the invariant",
   "benefit_direction": "no silent message loss from id collisions",
   "owner": "handoffs/active/coordination-and-churn-pipeline.md",
   "execution_conditions": "immediate, zero inference",
   "closure_basis": "Immediate code and doc; R6c screening folded in"
  },
  "K1": {
   "project_objective": "Retain the evidence standards without new work",
   "implementation_ref": "research/intake_index.yaml intake-2654, intake-2658",
   "gap": "no lane text records the registry posture or the exact-pin default",
   "operational_change": "knowledge rows only",
   "benefit_direction": "prevents re-derivation",
   "owner": "handoffs/active/harness-program.md",
   "execution_conditions": "no execution",
   "closure_basis": "Knowledge-only with grounded basis"
  },
  "M1": {
   "project_objective": "Gate inference-spending measurements on fired triggers",
   "implementation_ref": "harness-program.md measurement lanes",
   "gap": "the measurements need granted compute and a declared workload",
   "operational_change": "durable trigger prose",
   "benefit_direction": "no idle inference spend",
   "owner": "handoffs/active/harness-program.md",
   "execution_conditions": "only after the stated trigger",
   "closure_basis": "Monitor: no immediate step remains"
  }
 },
 "opportunity_scan": [
  {
   "scan_id": "S1",
   "source_ref": "intake-2650#0 (portable handoff contract, docs/user/portable-handoffs.md)",
   "implementation_ref": "coordination/session-bus/BUS_PROTOCOL.md lacks a context-transfer kind; CF-AB-1 A6 has three fields",
   "mechanism": "deterministic budgeted handoff with omitted-item pointers",
   "consumer": "cross-main takeover",
   "application": "A6 field set plus a handoff-transfer ledger",
   "disposition": "actionable",
   "ledger_ids": [
    "RI-11",
    "RI-12"
   ],
   "basis": "Read the verified source passage and the named current consumer at lane ec6aba4b1; the gap is absent from both the retained and the added ledger."
  },
  {
   "scan_id": "S2",
   "source_ref": "intake-2653#1 (seven deterministic + seven model-filled fields, App C)",
   "implementation_ref": "context-and-token-economy.md:117 A6 schema has three fields; /log renders an argv but not its evidence",
   "mechanism": "validation evidence is the highest-value handoff field; events, not tokens, are the stable signal",
   "consumer": "session resume and cross-main takeover",
   "application": "render validation evidence and add an events co-metric",
   "disposition": "actionable",
   "ledger_ids": [
    "RI-13",
    "RI-14"
   ],
   "basis": "Read the verified source passage and the named current consumer at lane ec6aba4b1; the gap is absent from both the retained and the added ledger."
  },
  {
   "scan_id": "S3",
   "source_ref": "intake-2658#0 (schema-epoch drift)",
   "implementation_ref": "src/typed_decisions/prepared_action.py rechecks catalog and read-set fingerprints, not interpreter identity",
   "mechanism": "a schema-valid stored call can change effect when the handler changes",
   "consumer": "typed-decision dispatch",
   "application": "fold serving identity into the dispatch fingerprint",
   "disposition": "actionable",
   "ledger_ids": [
    "RI-15",
    "RI-16"
   ],
   "basis": "Read the verified source passage and the named current consumer at lane ec6aba4b1; the gap is absent from both the retained and the added ledger."
  },
  {
   "scan_id": "S4",
   "source_ref": "intake-2652#0-1 (certificate binds args+receipt, proves omission)",
   "implementation_ref": "decision_receipt.v1 has validation_result but no validator identity or conclusion validity",
   "mechanism": "omission is not correctness and needs an evidence class",
   "consumer": "receipt consumers and any 'safely skipped' claim",
   "application": "add validator identity and an evidence-class rule",
   "disposition": "actionable",
   "ledger_ids": [
    "RI-17",
    "RI-18"
   ],
   "basis": "Read the verified source passage and the named current consumer at lane ec6aba4b1; the gap is absent from both the retained and the added ledger."
  },
  {
   "scan_id": "S5",
   "source_ref": "intake-2661#3 (guarantee is marginal and needs labels)",
   "implementation_ref": "no error-budget row exists in the harness, kv-cache or routing lanes",
   "mechanism": "a skip needs a denominator, not just a guard",
   "consumer": "any reuse or cache claim",
   "application": "state the rule; do not build a semantic cache",
   "disposition": "actionable",
   "ledger_ids": [
    "RI-19"
   ],
   "basis": "Read the verified source passage and the named current consumer at lane ec6aba4b1; the gap is absent from both the retained and the added ledger."
  },
  {
   "scan_id": "S6",
   "source_ref": "intake-2659#2-3 (no grid control, noise floor understated)",
   "implementation_ref": "harness-program.md has no claim-grammar rule for token savings",
   "mechanism": "attribution needs a call-count decomposition and a control",
   "consumer": "harness reporting",
   "application": "claim grammar plus an attribution note",
   "disposition": "actionable",
   "ledger_ids": [
    "RI-20"
   ],
   "basis": "Read the verified source passage and the named current consumer at lane ec6aba4b1; the gap is absent from both the retained and the added ledger."
  },
  {
   "scan_id": "S7",
   "source_ref": "intake-2656#2 (authoring cost, 39-101 task break-even)",
   "implementation_ref": "harness-program.md:417 prices per-task cost only; :2447 is the build-cost precedent",
   "mechanism": "reuse mechanisms carry a one-time authoring cost",
   "consumer": "harness feature reporting",
   "application": "authoring-cost column",
   "disposition": "actionable",
   "ledger_ids": [
    "RI-21"
   ],
   "basis": "Read the verified source passage and the named current consumer at lane ec6aba4b1; the gap is absent from both the retained and the added ledger."
  },
  {
   "scan_id": "S8",
   "source_ref": "intake-2657#2 (three-group evidence checklist)",
   "implementation_ref": "no per-transition admission row exists in harness-program.md",
   "mechanism": "evidence classes for admitting a stored action",
   "consumer": "tool-dispatch admission",
   "application": "fold into the evidence-class rule, do not duplicate",
   "disposition": "context-only",
   "ledger_ids": [
    "RI-18"
   ],
   "basis": "Read the verified source passage and the named current consumer at lane ec6aba4b1; the gap is absent from both the retained and the added ledger."
  },
  {
   "scan_id": "S9",
   "source_ref": "intake-2651#3 (device-tier + cached-first variant selection)",
   "implementation_ref": "master-model-registry.yaml has one model per role and no (backend, device) variant",
   "mechanism": "hardware detection and variant selection as a data contract",
   "consumer": "model registry and stack priors",
   "application": "add host capabilities and a variant dimension",
   "disposition": "actionable",
   "ledger_ids": [
    "RI-22",
    "RI-23"
   ],
   "basis": "Read the verified source passage and the named current consumer at lane ec6aba4b1; the gap is absent from both the retained and the added ledger."
  },
  {
   "scan_id": "S10",
   "source_ref": "intake-2655#i-ii (rebuild and boundary receipts)",
   "implementation_ref": "BUS_PROTOCOL rule 9 and rebuild_state already satisfy the durable-record requirement; append does not enforce id uniqueness",
   "mechanism": "unbounded dedup is by construction, but id collisions can lose messages",
   "consumer": "session bus",
   "application": "fix append and record the invariant",
   "disposition": "actionable",
   "ledger_ids": [
    "RI-24",
    "RI-25"
   ],
   "basis": "Read the verified source passage and the named current consumer at lane ec6aba4b1; the gap is absent from both the retained and the added ledger."
  },
  {
   "scan_id": "S11",
   "source_ref": "intake-2654#2 (nightly capability matrix)",
   "implementation_ref": "harness-program.md:362 keeps ACP dormant; client-surface-audit.md:102 requires re-check on pin bump",
   "mechanism": "nightly launch-and-probe capability diff",
   "consumer": "harness pin audits",
   "application": "borrow the pattern; do not consume the registry",
   "disposition": "context-only",
   "ledger_ids": [
    "RI-26"
   ],
   "basis": "Read the verified source passage and the named current consumer at lane ec6aba4b1; the gap is absent from both the retained and the added ledger."
  },
  {
   "scan_id": "S13",
   "source_ref": "intake-2651#record, intake-2652#record, intake-2654#record, intake-2656#record, intake-2658#record, intake-2659#record, intake-2660#record, intake-2661#record",
   "implementation_ref": "the named lanes have no task for any of these mechanisms; each decline was checked against the lane implementation",
   "mechanism": "shipping systems whose costs or prerequisites outweigh the gap they would close",
   "consumer": "EPYC harness and serving",
   "application": "decline with the recorded reason",
   "disposition": "declined",
   "ledger_ids": [
    "RI-01",
    "RI-02",
    "RI-03",
    "RI-04",
    "RI-05",
    "RI-06",
    "RI-07",
    "RI-08",
    "RI-09",
    "RI-10"
   ],
   "basis": "Read the verified source passage and the named current consumer at lane ec6aba4b1; the gap is absent from both the retained and the added ledger."
  },
  {
   "scan_id": "S14",
   "source_ref": "intake-2656#3 (state-machine memory), intake-2659#1 (nine flags)",
   "implementation_ref": "harness-program.md has no vocabulary separating prompt/prefix reuse from environment or action reuse",
   "mechanism": "different reuse substrates have different invalidation sets",
   "consumer": "harness reuse reporting",
   "application": "register the substrates and require attribution controls",
   "disposition": "actionable",
   "ledger_ids": [
    "RI-27",
    "RI-28"
   ],
   "basis": "Read the verified source passage and the named current consumer at lane ec6aba4b1; the gap is absent from both the retained and the added ledger."
  },
  {
   "scan_id": "S15",
   "source_ref": "intake-2655#iii (no dedup horizon)",
   "implementation_ref": "coordination-and-churn-pipeline.md:437-441 R6c rationale predates rebuild_state",
   "mechanism": "the record may already carry mid-task and gate state",
   "consumer": "coordinator resume",
   "application": "re-screen R6c",
   "disposition": "actionable",
   "ledger_ids": [
    "RI-29"
   ],
   "basis": "Read the verified source passage and the named current consumer at lane ec6aba4b1; the gap is absent from both the retained and the added ledger."
  },
  {
   "scan_id": "S16",
   "source_ref": "intake-2658#1 (authority captured at formation)",
   "implementation_ref": "no lane row states the stored-call default",
   "mechanism": "exact pinning is the paper's safe arm and our calls are cheap to re-form",
   "consumer": "stored and replayed tool calls",
   "application": "record exact-pin as the default",
   "disposition": "context-only",
   "ledger_ids": [
    "RI-30"
   ],
   "basis": "Read the verified source passage and the named current consumer at lane ec6aba4b1; the gap is absent from both the retained and the added ledger."
  },
  {
   "scan_id": "S17",
   "source_ref": "intake-2652#5, intake-2653#5, intake-2657#5, intake-2650#6, intake-2651#5",
   "implementation_ref": "each measurement needs granted compute or a workload that does not exist yet",
   "mechanism": "inference-gated probes",
   "consumer": "harness and routing lanes",
   "application": "durable triggers only",
   "disposition": "context-only",
   "ledger_ids": [
    "M-1",
    "M-2",
    "M-3",
    "M-4",
    "M-5"
   ],
   "basis": "Read the verified source passage and the named current consumer at lane ec6aba4b1; the gap is absent from both the retained and the added ledger."
  }
 ],
 "actionable_additions": [
  {
   "ledger_id": "RI-11",
   "source": "intake-2650#4",
   "action": "Amend CF-AB-1 A6 to the measured field set and add an events co-metric",
   "terminal_mapping": "P2 / CTX-HO-1"
  },
  {
   "ledger_id": "RI-12",
   "source": "intake-2650#3",
   "action": "Add a typed handoff-transfer record and ledger to the session bus",
   "terminal_mapping": "P2 / CTX-HO-2"
  },
  {
   "ledger_id": "RI-13",
   "source": "intake-2653#1",
   "action": "Render validation evidence into the /log checkpoint envelope",
   "terminal_mapping": "P2 / CTX-HO-3"
  },
  {
   "ledger_id": "RI-14",
   "source": "intake-2653#2",
   "action": "Add events-per-solved-task as an A6 co-metric",
   "terminal_mapping": "P2 / CTX-HO-1"
  },
  {
   "ledger_id": "RI-15",
   "source": "intake-2658#0",
   "action": "Fold serving identity into the dispatch-time prepared-action recheck",
   "terminal_mapping": "P1 / UFH-TE-2"
  },
  {
   "ledger_id": "RI-16",
   "source": "intake-2658#1",
   "action": "Constrain any omission certificate to three added fields and exact-pin the default",
   "terminal_mapping": "P1 / UFH-TE-3"
  },
  {
   "ledger_id": "RI-17",
   "source": "intake-2660#0",
   "action": "Add validator identity and a conclusion validity interval to the receipt",
   "terminal_mapping": "P1 / UFH-TE-1"
  },
  {
   "ledger_id": "RI-18",
   "source": "intake-2657#2",
   "action": "Declare admissible evidence classes for any skipped or reused call",
   "terminal_mapping": "P1 / UFH-TE-3"
  },
  {
   "ledger_id": "RI-19",
   "source": "intake-2661#3",
   "action": "Refuse statistical language for a skip without an audited denominator",
   "terminal_mapping": "P1 / UFH-TE-3"
  },
  {
   "ledger_id": "RI-20",
   "source": "intake-2652#1",
   "action": "Require a call-count decomposition on every token-saving claim",
   "terminal_mapping": "P3 / HIL-RE-1"
  },
  {
   "ledger_id": "RI-21",
   "source": "intake-2656#2",
   "action": "Add an authoring-cost column to the S4 reporting contract",
   "terminal_mapping": "P3 / HIL-RE-4"
  },
  {
   "ledger_id": "RI-22",
   "source": "intake-2651#2",
   "action": "Emit a host-capability manifest as a compiled input",
   "terminal_mapping": "P4 / RTG-VAR-1"
  },
  {
   "ledger_id": "RI-23",
   "source": "intake-2651#3",
   "action": "Add a variant dimension to the model descriptor",
   "terminal_mapping": "P4 / RTG-VAR-2"
  },
  {
   "ledger_id": "RI-24",
   "source": "intake-2655#i",
   "action": "Refuse duplicate message ids in session_bus append",
   "terminal_mapping": "P5 / BUS-ID-1"
  },
  {
   "ledger_id": "RI-25",
   "source": "intake-2655#iii",
   "action": "Record the unbounded-dedup invariant in BUS_PROTOCOL",
   "terminal_mapping": "P5 / BUS-ID-2"
  },
  {
   "ledger_id": "RI-26",
   "source": "intake-2654#3",
   "action": "Borrow the nightly capability-diff pattern for pin audits",
   "terminal_mapping": "K1 / knowledge-only"
  },
  {
   "ledger_id": "RI-27",
   "source": "intake-2652#2",
   "action": "Register non-prompt reuse substrates with invalidation sets",
   "terminal_mapping": "P3 / HIL-RE-2"
  },
  {
   "ledger_id": "RI-28",
   "source": "intake-2659#2",
   "action": "Add a telemetry read/write-asymmetry invariant",
   "terminal_mapping": "P3 / HIL-RE-3"
  },
  {
   "ledger_id": "RI-29",
   "source": "intake-2653#3",
   "action": "Re-screen the R6c post-reboot brief against rebuild_state",
   "terminal_mapping": "P5 / BUS-ID-3"
  },
  {
   "ledger_id": "RI-30",
   "source": "intake-2658#0",
   "action": "Exact-pin stored and replayed calls by default; record the re-formation cost",
   "terminal_mapping": "K1 / knowledge-only"
  },
  {
   "ledger_id": "RI-01",
   "source": "intake-2650#record",
   "action": "Port T3's SQL event store, projections, command receipts and outbox into EPYC",
   "terminal_mapping": "decline: Bus rule 1 (single writer per file) and rule 9 (rebuildable from files) are incompatible with a central store; T3's own recovery is a read-only copy of userdata with no export API. Kept as design reading only."
  },
  {
   "ledger_id": "RI-02",
   "source": "intake-2651#record",
   "action": "Port Foundry's first-use download and content-addressed cache",
   "terminal_mapping": "decline: EPYC's 162 model paths are pre-staged locally with sha256 pinned; a downloader solves a problem we do not have (dive port-cost estimate: +3-5 days for zero benefit)."
  },
  {
   "ledger_id": "RI-03",
   "source": "intake-2651#record",
   "action": "Treat Foundry Local as a serving runtime candidate",
   "terminal_mapping": "decline: ONNX-only, no ROCm EP shipped, single-user with no batching; the MI210 path would require model conversion plus a quality-parity study, for a runtime that cannot serve our workload."
  },
  {
   "ledger_id": "RI-04",
   "source": "intake-2652#record",
   "action": "Reproduce the HumanEval and MBPP arms",
   "terminal_mapping": "decline: Hosted harnesses, a self-hosted Qwen3.5-4B actor, no time axis; nothing transfers that the wall-clock probe does not already answer."
  },
  {
   "ledger_id": "RI-05",
   "source": "intake-2659#record",
   "action": "Build a Bayesian harness-flag search",
   "terminal_mapping": "decline: The paper's own pick ties the manual peak within a corrected +/-5.9-pass interval, has no random/grid control, and is warm-started from the manual log; cost is 35-98% of a week's quota. EPYC's flag space is ~10-20 dims where random/OAT is the correct baseline."
  },
  {
   "ledger_id": "RI-06",
   "source": "intake-2660#record",
   "action": "Adopt CORTEX's experience graph, decisive predicates, proof trace or four-mode controller for dispatch",
   "terminal_mapping": "decline: EPYC re-dispatches rather than reuses, so replay warrants buy nothing; the paper's own cost is higher warm latency and +24-30% reasoning work for zero label gain. Two fields are retained instead (validator identity, conclusion validity)."
  },
  {
   "ledger_id": "RI-07",
   "source": "intake-2658#record",
   "action": "Port the reviewed effect-profile pipeline, registrar and admission plane",
   "terminal_mapping": "decline: Soundness rests on a reviewed profile premise and a call-site classifier our tool surface cannot support; single-host harness with no registry. Keep the ordering rule and the three-field epoch binding only."
  },
  {
   "ledger_id": "RI-08",
   "source": "intake-2661#record",
   "action": "Build a semantic answer cache with an error bound",
   "terminal_mapping": "decline: Our reuse is exact (prefix cache, ~99% of prompt tokens), which satisfies correctness trivially; a semantic cache adds a quality risk and a calibration burden for throughput we do not need. Revisit only if an approximate reuse tier is proposed AND a rate-tau audit is affordable."
  },
  {
   "ledger_id": "RI-09",
   "source": "intake-2654#record",
   "action": "Consume the ACP registry as a runtime trust source",
   "terminal_mapping": "decline: The registry is an agent catalog with no capability fields in the published index, quarantine is invisible to clients, and 7 of 22 binary manifests ship no sha256. It removes no EPYC work because ACP is a north-facing editor protocol and our injection point is south-facing; pin-source discipline and the capability-diff pattern are borrowed instead."
  },
  {
   "ledger_id": "RI-10",
   "source": "intake-2654#record",
   "action": "Treat ecosystem growth as evidence for or against the ACP verdict",
   "terminal_mapping": "decline: The verdict is layer-based (north vs south), not adoption-based; agent counts do not move it."
  },
  {
   "ledger_id": "M-1",
   "source": "intake-2653#5",
   "action": "Paired EPYC handoff-debt measurement: repository-only vs rendered note, n>=10 checkpoints, calls and cold-prefill seconds",
   "terminal_mapping": "M1"
  },
  {
   "ledger_id": "M-2",
   "source": "intake-2652#5",
   "action": "60-pair ABBA wall-clock probe of literal-action reuse with the six controls",
   "terminal_mapping": "M1"
  },
  {
   "ledger_id": "M-3",
   "source": "intake-2657#5",
   "action": "Non-LLM share of a tool turn (futility gate) and an idempotence census of the top tools",
   "terminal_mapping": "M1"
  },
  {
   "ledger_id": "M-4",
   "source": "intake-2650#6",
   "action": "Session-identity capability column (can_resume/fork/rollback/max_context) before any native transfer",
   "terminal_mapping": "M1"
  },
  {
   "ledger_id": "M-5",
   "source": "intake-2651#5",
   "action": "Variant selector implementation only after the descriptor and host manifest exist",
   "terminal_mapping": "M1"
  }
 ],
 "steering_reconciliation": [
  {
   "seq": 1,
   "stage": 1,
   "ts": "2026-11-06T23:23:08.921908+00:00",
   "verbatim": "Run the research-intake skill on this sources: https://github.com/pingdotgg/t3code, https://github.com/microsoft/foundry-local, https://arxiv.org/html/2610.32813v1. Accept all recommended deep dives for up to four Stage 2 waves. The sources concern topics pertaining to inference and harness optimizations.",
   "disposition": "planned",
   "plan_ref": "P1",
   "reason": "All 12 dives ran across exactly four waves as authorised; the resulting actionables are the P1-P5 packets, K1 and M1 triggers in this plan."
  }
 ],
 "outcome_reviews": {
  "RI-11": {
   "required_outcome": "Amend CF-AB-1 A6 to the measured field set and add an events co-metric",
   "review_status": "preserved",
   "review_basis": "Immediate work mapped to CTX-HO-1; the task's acceptance is the operational outcome, and no activation gate is implied.",
   "task_refs": [
    {
     "owner": "handoffs/active/context-and-token-economy.md",
     "task_id": "CTX-HO-1",
     "task_text": "- [ ] **CTX-HO-1 — Amend CF-AB-1 A6 to the measured handoff field set and co-metric.** Replace A6's three-field schema with the seven deterministic fields (repository change state, changed source files, non-source artifacts, validation outcome, latest validation command, latest validation evidence, continuation-state label) and seven model-filled fields; add `events per solved task` beside uncached prefill as a co-metric. Acceptance: A6 text carries both field lists and both metrics; no new arm.",
     "acceptance": "A6 text carries both field lists and both metrics; no new arm."
    }
   ]
  },
  "RI-12": {
   "required_outcome": "Add a typed handoff-transfer record and ledger to the session bus",
   "review_status": "preserved",
   "review_basis": "Immediate work mapped to CTX-HO-2; the task's acceptance is the operational outcome, and no activation gate is implied.",
   "task_refs": [
    {
     "owner": "handoffs/active/coordination-and-churn-pipeline.md",
     "task_id": "CTX-HO-2",
     "task_text": "- [ ] **CTX-HO-2 — Add a typed handoff-transfer record and ledger to the session bus.** Add a `handoff-transfer` message kind and a coordinator-owned append-only `transfers/` ledger with transfer_id, source point, base point, coverage, selected and omitted ids, budget_bytes, status, consumer, consumed_at; lazy resolution on first dispatch; ack deduped on transfer_id. Acceptance: schema, single-writer rule and a two-main fixture test.",
     "acceptance": "schema, single-writer rule and a two-main fixture test."
    }
   ]
  },
  "RI-13": {
   "required_outcome": "Render validation evidence into the /log checkpoint envelope",
   "review_status": "preserved",
   "review_basis": "Immediate work mapped to CTX-HO-3; the task's acceptance is the operational outcome, and no activation gate is implied.",
   "task_refs": [
    {
     "owner": "handoffs/active/context-and-token-economy.md",
     "task_id": "CTX-HO-3",
     "task_text": "- [ ] **CTX-HO-3 — Render validation evidence into the /log checkpoint envelope.** The completed-checkpoint envelope carries a `resume_state` block with the latest validation command, its observed output or exit, remaining uncertainty, a rollback note, non-source artifacts and a continuation-state label. Acceptance: a real checkpoint renders a populated block from the executed `--validation-json`; missing evidence renders as explicitly unknown.",
     "acceptance": "a real checkpoint renders a populated block from the executed `--validation-json`; missing evidence renders as explicitly unknown."
    }
   ]
  },
  "RI-14": {
   "required_outcome": "Add events-per-solved-task as an A6 co-metric",
   "review_status": "preserved",
   "review_basis": "Immediate work mapped to CTX-HO-1; the task's acceptance is the operational outcome, and no activation gate is implied.",
   "task_refs": [
    {
     "owner": "handoffs/active/context-and-token-economy.md",
     "task_id": "CTX-HO-1",
     "task_text": "- [ ] **CTX-HO-1 — Amend CF-AB-1 A6 to the measured handoff field set and co-metric.** Replace A6's three-field schema with the seven deterministic fields (repository change state, changed source files, non-source artifacts, validation outcome, latest validation command, latest validation evidence, continuation-state label) and seven model-filled fields; add `events per solved task` beside uncached prefill as a co-metric. Acceptance: A6 text carries both field lists and both metrics; no new arm.",
     "acceptance": "A6 text carries both field lists and both metrics; no new arm."
    }
   ]
  },
  "RI-15": {
   "required_outcome": "Fold serving identity into the dispatch-time prepared-action recheck",
   "review_status": "preserved",
   "review_basis": "Immediate work mapped to UFH-TE-2; the task's acceptance is the operational outcome, and no activation gate is implied.",
   "task_refs": [
    {
     "owner": "handoffs/active/harness-program.md",
     "task_id": "UFH-TE-2",
     "task_text": "- [ ] **UFH-TE-2 — Fold serving identity into the dispatch-time prepared-action recheck.** Extend the dispatch fingerprint with descriptor digest, handler artifact and config digest, serving process start time and serving tree commit. A mismatch returns `stale` and routes to re-form; stored calls are never executed silently. Acceptance: a synthetic handler swap between formation and dispatch produces `stale`, a benign restart does not, and a regression test pins both.",
     "acceptance": "a synthetic handler swap between formation and dispatch produces `stale`, a benign restart does not, and a regression test pins both."
    }
   ]
  },
  "RI-16": {
   "required_outcome": "Constrain any omission certificate to three added fields and exact-pin the default",
   "review_status": "preserved",
   "review_basis": "Immediate work mapped to UFH-TE-3; the task's acceptance is the operational outcome, and no activation gate is implied.",
   "task_refs": [
    {
     "owner": "handoffs/active/harness-program.md",
     "task_id": "UFH-TE-3",
     "task_text": "- [ ] **UFH-TE-3 — Declare admissible evidence classes for any skipped or reused call.** Write the rule that a 'safely skipped' or 'reused' claim names one of: identity receipt (the call was executed with a bound receipt), rate-tau audited population (a fraction of skips are recomputed and scored), or none. Forbid statistical language without an audited denominator. Acceptance: the rule is in the receipt contract and a lint check flags any handoff sentence that claims a skip without a class.",
     "acceptance": "the rule is in the receipt contract and a lint check flags any handoff sentence that claims a skip without a class."
    }
   ]
  },
  "RI-17": {
   "required_outcome": "Add validator identity and a conclusion validity interval to the receipt",
   "review_status": "preserved",
   "review_basis": "Immediate work mapped to UFH-TE-1; the task's acceptance is the operational outcome, and no activation gate is implied.",
   "task_refs": [
    {
     "owner": "handoffs/active/harness-program.md",
     "task_id": "UFH-TE-1",
     "task_text": "- [ ] **UFH-TE-1 — Add validator identity and a conclusion validity interval to the decision receipt.** Extend `decision_receipt.v1` with `validator_id`, `validator_version` and `conclusion_valid_until_ns` (all optional, default None; no behaviour change). Acceptance: the schema and the producer emit the fields; an existing receipt without them still validates; no gate changes.",
     "acceptance": "the schema and the producer emit the fields; an existing receipt without them still validates; no gate changes."
    }
   ]
  },
  "RI-18": {
   "required_outcome": "Declare admissible evidence classes for any skipped or reused call",
   "review_status": "preserved",
   "review_basis": "Immediate work mapped to UFH-TE-3; the task's acceptance is the operational outcome, and no activation gate is implied.",
   "task_refs": [
    {
     "owner": "handoffs/active/harness-program.md",
     "task_id": "UFH-TE-3",
     "task_text": "- [ ] **UFH-TE-3 — Declare admissible evidence classes for any skipped or reused call.** Write the rule that a 'safely skipped' or 'reused' claim names one of: identity receipt (the call was executed with a bound receipt), rate-tau audited population (a fraction of skips are recomputed and scored), or none. Forbid statistical language without an audited denominator. Acceptance: the rule is in the receipt contract and a lint check flags any handoff sentence that claims a skip without a class.",
     "acceptance": "the rule is in the receipt contract and a lint check flags any handoff sentence that claims a skip without a class."
    }
   ]
  },
  "RI-19": {
   "required_outcome": "Refuse statistical language for a skip without an audited denominator",
   "review_status": "preserved",
   "review_basis": "Immediate work mapped to UFH-TE-3; the task's acceptance is the operational outcome, and no activation gate is implied.",
   "task_refs": [
    {
     "owner": "handoffs/active/harness-program.md",
     "task_id": "UFH-TE-3",
     "task_text": "- [ ] **UFH-TE-3 — Declare admissible evidence classes for any skipped or reused call.** Write the rule that a 'safely skipped' or 'reused' claim names one of: identity receipt (the call was executed with a bound receipt), rate-tau audited population (a fraction of skips are recomputed and scored), or none. Forbid statistical language without an audited denominator. Acceptance: the rule is in the receipt contract and a lint check flags any handoff sentence that claims a skip without a class.",
     "acceptance": "the rule is in the receipt contract and a lint check flags any handoff sentence that claims a skip without a class."
    }
   ]
  },
  "RI-20": {
   "required_outcome": "Require a call-count decomposition on every token-saving claim",
   "review_status": "preserved",
   "review_basis": "Immediate work mapped to HIL-RE-1; the task's acceptance is the operational outcome, and no activation gate is implied.",
   "task_refs": [
    {
     "owner": "handoffs/active/harness-program.md",
     "task_id": "HIL-RE-1",
     "task_text": "- [ ] **HIL-RE-1 — Require a call-count decomposition on every token-saving claim.** Any harness token-saving figure we cite or produce must state delta calls (certified bypasses vs other), tokens/call before and after, and whether the effect is prefill or decode. A saving that cannot be decomposed this way may not be described as callback elimination. Acceptance: the reporting convention text and one worked example from intake-2652.",
     "acceptance": "the reporting convention text and one worked example from intake-2652."
    }
   ]
  },
  "RI-21": {
   "required_outcome": "Add an authoring-cost column to the S4 reporting contract",
   "review_status": "preserved",
   "review_basis": "Immediate work mapped to HIL-RE-4; the task's acceptance is the operational outcome, and no activation gate is implied.",
   "task_refs": [
    {
     "owner": "handoffs/active/harness-program.md",
     "task_id": "HIL-RE-4",
     "task_text": "- [ ] **HIL-RE-4 — Add an authoring-cost column to the S4 reporting contract.** Any reuse-bearing harness feature reports one-time authoring cost in dollars and engineer-hours, the break-even N against the paired baseline, whether that N is per-artefact or cross-artefact, and build cost separately from steady state. Acceptance: the S4 contract text carries the four fields.",
     "acceptance": "the S4 contract text carries the four fields."
    }
   ]
  },
  "RI-22": {
   "required_outcome": "Emit a host-capability manifest as a compiled input",
   "review_status": "preserved",
   "review_basis": "Immediate work mapped to RTG-VAR-1; the task's acceptance is the operational outcome, and no activation gate is implied.",
   "task_refs": [
    {
     "owner": "handoffs/active/routing-program.md",
     "task_id": "RTG-VAR-1",
     "task_text": "- [ ] **RTG-VAR-1 — Emit a host-capability manifest as a compiled input.** Add `orchestration/host_capabilities.yaml` (CPU flags, NUMA nodes, GPU arch and VRAM, ROCm version, RAM) probed from the existing inventory scripts and consumed by the registry compiler. Acceptance: the manifest is generated reproducibly and a golden test pins its shape.",
     "acceptance": "the manifest is generated reproducibly and a golden test pins its shape."
    }
   ]
  },
  "RI-23": {
   "required_outcome": "Add a variant dimension to the model descriptor",
   "review_status": "preserved",
   "review_basis": "Immediate work mapped to RTG-VAR-2; the task's acceptance is the operational outcome, and no activation gate is implied.",
   "task_refs": [
    {
     "owner": "handoffs/active/routing-program.md",
     "task_id": "RTG-VAR-2",
     "task_text": "- [ ] **RTG-VAR-2 — Add a variant dimension to the model descriptor.** Extend the descriptor with `variants: [{quant, backend, device, path, sha256, ctx_max, measured_tps, quality_ref}]`, seeded from existing role entries and normalising the free-form quant strings. Acceptance: schema plus a migration that resolves all existing roles to at least one variant with no invented measurement.",
     "acceptance": "schema plus a migration that resolves all existing roles to at least one variant with no invented measurement."
    }
   ]
  },
  "RI-24": {
   "required_outcome": "Refuse duplicate message ids in session_bus append",
   "review_status": "preserved",
   "review_basis": "Immediate work mapped to BUS-ID-1; the task's acceptance is the operational outcome, and no activation gate is implied.",
   "task_refs": [
    {
     "owner": "handoffs/active/coordination-and-churn-pipeline.md",
     "task_id": "BUS-ID-1",
     "task_text": "- [ ] **BUS-ID-1 — Refuse duplicate message ids in session_bus append.** `cmd_append` exits non-zero when a caller-supplied id already exists in the destination, instead of trusting it; add a regression test. Acceptance: a second append with the same explicit id fails and leaves one row.",
     "acceptance": "a second append with the same explicit id fails and leaves one row."
    }
   ]
  },
  "RI-25": {
   "required_outcome": "Record the unbounded-dedup invariant in BUS_PROTOCOL",
   "review_status": "preserved",
   "review_basis": "Immediate work mapped to BUS-ID-2; the task's acceptance is the operational outcome, and no activation gate is implied.",
   "task_refs": [
    {
     "owner": "handoffs/active/coordination-and-churn-pipeline.md",
     "task_id": "BUS-ID-2",
     "task_text": "- [ ] **BUS-ID-2 — Record the unbounded-dedup invariant in BUS_PROTOCOL.** State that messages never expire, retention is cursor-gated, `--stale-after-h` labels but never drops, and a time-bounded TTL must not be introduced. Acceptance: the invariant appears with the rule number and the code references.",
     "acceptance": "the invariant appears with the rule number and the code references."
    }
   ]
  },
  "RI-26": {
   "required_outcome": "Borrow the nightly capability-diff pattern for pin audits",
   "review_status": "closed-with-basis",
   "review_basis": "Retained as knowledge: the mechanism is documented in the intake entry and the lane decision record; no implementation task is justified because the current consumer already satisfies the need (see opportunity scan).",
   "task_refs": []
  },
  "RI-27": {
   "required_outcome": "Register non-prompt reuse substrates with invalidation sets",
   "review_status": "preserved",
   "review_basis": "Immediate work mapped to HIL-RE-2; the task's acceptance is the operational outcome, and no activation gate is implied.",
   "task_refs": [
    {
     "owner": "handoffs/active/harness-program.md",
     "task_id": "HIL-RE-2",
     "task_text": "- [ ] **HIL-RE-2 — Register non-prompt reuse substrates with their invalidation sets.** One knowledge row naming per-operation graph reuse, per-action decision-graph reuse and prefix-cache reuse as distinct mechanisms, each with what invalidates it. Acceptance: the row exists and no existing reuse task is duplicated.",
     "acceptance": "the row exists and no existing reuse task is duplicated."
    }
   ]
  },
  "RI-28": {
   "required_outcome": "Add a telemetry read/write-asymmetry invariant",
   "review_status": "preserved",
   "review_basis": "Immediate work mapped to HIL-RE-3; the task's acceptance is the operational outcome, and no activation gate is implied.",
   "task_refs": [
    {
     "owner": "handoffs/active/harness-program.md",
     "task_id": "HIL-RE-3",
     "task_text": "- [ ] **HIL-RE-3 — Add a telemetry read/write-asymmetry invariant for harness flags.** When a flag fires on the write side but its consumer counter is identically zero, mark it silent, exclude it from any sweep and emit one typed event. Acceptance: a synthetic unwired consumer trips the check; a clean run is silent; no inference.",
     "acceptance": "a synthetic unwired consumer trips the check; a clean run is silent; no inference."
    }
   ]
  },
  "RI-29": {
   "required_outcome": "Re-screen the R6c post-reboot brief against rebuild_state",
   "review_status": "preserved",
   "review_basis": "Immediate work mapped to BUS-ID-3; the task's acceptance is the operational outcome, and no activation gate is implied.",
   "task_refs": [
    {
     "owner": "handoffs/active/coordination-and-churn-pipeline.md",
     "task_id": "BUS-ID-3",
     "task_text": "- [ ] **BUS-ID-3 — Re-screen the R6c post-reboot brief against current rebuild_state.** Check whether rebuild now derives tokens, heartbeat task_id, leases and checkpoint fields; if so, narrow or close R6c. Acceptance: a dated screening note, not a new task.",
     "acceptance": "a dated screening note, not a new task."
    }
   ]
  },
  "RI-30": {
   "required_outcome": "Exact-pin stored and replayed calls by default; record the re-formation cost",
   "review_status": "closed-with-basis",
   "review_basis": "Retained as knowledge: the mechanism is documented in the intake entry and the lane decision record; no implementation task is justified because the current consumer already satisfies the need (see opportunity scan).",
   "task_refs": []
  },
  "RI-01": {
   "required_outcome": "Port T3's SQL event store, projections, command receipts and outbox into EPYC",
   "review_status": "closed-with-basis",
   "review_basis": "Bus rule 1 (single writer per file) and rule 9 (rebuildable from files) are incompatible with a central store; T3's own recovery is a read-only copy of userdata with no export API. Kept as design reading only.",
   "task_refs": []
  },
  "RI-02": {
   "required_outcome": "Port Foundry's first-use download and content-addressed cache",
   "review_status": "closed-with-basis",
   "review_basis": "EPYC's 162 model paths are pre-staged locally with sha256 pinned; a downloader solves a problem we do not have (dive port-cost estimate: +3-5 days for zero benefit).",
   "task_refs": []
  },
  "RI-03": {
   "required_outcome": "Treat Foundry Local as a serving runtime candidate",
   "review_status": "closed-with-basis",
   "review_basis": "ONNX-only, no ROCm EP shipped, single-user with no batching; the MI210 path would require model conversion plus a quality-parity study, for a runtime that cannot serve our workload.",
   "task_refs": []
  },
  "RI-04": {
   "required_outcome": "Reproduce the HumanEval and MBPP arms",
   "review_status": "closed-with-basis",
   "review_basis": "Hosted harnesses, a self-hosted Qwen3.5-4B actor, no time axis; nothing transfers that the wall-clock probe does not already answer.",
   "task_refs": []
  },
  "RI-05": {
   "required_outcome": "Build a Bayesian harness-flag search",
   "review_status": "closed-with-basis",
   "review_basis": "The paper's own pick ties the manual peak within a corrected +/-5.9-pass interval, has no random/grid control, and is warm-started from the manual log; cost is 35-98% of a week's quota. EPYC's flag space is ~10-20 dims where random/OAT is the correct baseline.",
   "task_refs": []
  },
  "RI-06": {
   "required_outcome": "Adopt CORTEX's experience graph, decisive predicates, proof trace or four-mode controller for dispatch",
   "review_status": "closed-with-basis",
   "review_basis": "EPYC re-dispatches rather than reuses, so replay warrants buy nothing; the paper's own cost is higher warm latency and +24-30% reasoning work for zero label gain. Two fields are retained instead (validator identity, conclusion validity).",
   "task_refs": []
  },
  "RI-07": {
   "required_outcome": "Port the reviewed effect-profile pipeline, registrar and admission plane",
   "review_status": "closed-with-basis",
   "review_basis": "Soundness rests on a reviewed profile premise and a call-site classifier our tool surface cannot support; single-host harness with no registry. Keep the ordering rule and the three-field epoch binding only.",
   "task_refs": []
  },
  "RI-08": {
   "required_outcome": "Build a semantic answer cache with an error bound",
   "review_status": "closed-with-basis",
   "review_basis": "Our reuse is exact (prefix cache, ~99% of prompt tokens), which satisfies correctness trivially; a semantic cache adds a quality risk and a calibration burden for throughput we do not need. Revisit only if an approximate reuse tier is proposed AND a rate-tau audit is affordable.",
   "task_refs": []
  },
  "RI-09": {
   "required_outcome": "Consume the ACP registry as a runtime trust source",
   "review_status": "closed-with-basis",
   "review_basis": "The registry is an agent catalog with no capability fields in the published index, quarantine is invisible to clients, and 7 of 22 binary manifests ship no sha256. It removes no EPYC work because ACP is a north-facing editor protocol and our injection point is south-facing; pin-source discipline and the capability-diff pattern are borrowed instead.",
   "task_refs": []
  },
  "RI-10": {
   "required_outcome": "Treat ecosystem growth as evidence for or against the ACP verdict",
   "review_status": "closed-with-basis",
   "review_basis": "The verdict is layer-based (north vs south), not adoption-based; agent counts do not move it.",
   "task_refs": []
  },
  "M-1": {
   "required_outcome": "Paired EPYC handoff-debt measurement: repository-only vs rendered note, n>=10 checkpoints, calls and cold-prefill seconds",
   "review_status": "closed-with-basis",
   "review_basis": "Trigger-gated: a durable monitor record with no active checkbox; materialise only when its stated trigger fires.",
   "task_refs": []
  },
  "M-2": {
   "required_outcome": "60-pair ABBA wall-clock probe of literal-action reuse with the six controls",
   "review_status": "closed-with-basis",
   "review_basis": "Trigger-gated: a durable monitor record with no active checkbox; materialise only when its stated trigger fires.",
   "task_refs": []
  },
  "M-3": {
   "required_outcome": "Non-LLM share of a tool turn (futility gate) and an idempotence census of the top tools",
   "review_status": "closed-with-basis",
   "review_basis": "Trigger-gated: a durable monitor record with no active checkbox; materialise only when its stated trigger fires.",
   "task_refs": []
  },
  "M-4": {
   "required_outcome": "Session-identity capability column (can_resume/fork/rollback/max_context) before any native transfer",
   "review_status": "closed-with-basis",
   "review_basis": "Trigger-gated: a durable monitor record with no active checkbox; materialise only when its stated trigger fires.",
   "task_refs": []
  },
  "M-5": {
   "required_outcome": "Variant selector implementation only after the descriptor and host manifest exist",
   "review_status": "closed-with-basis",
   "review_basis": "Trigger-gated: a durable monitor record with no active checkbox; materialise only when its stated trigger fires.",
   "task_refs": []
  }
 },
 "proposed_tasks": [
  {
   "owner": "handoffs/active/harness-program.md",
   "task_text": "- [ ] **UFH-TE-1 — Add validator identity and a conclusion validity interval to the decision receipt.** Extend `decision_receipt.v1` with `validator_id`, `validator_version` and `conclusion_valid_until_ns` (all optional, default None; no behaviour change). Acceptance: the schema and the producer emit the fields; an existing receipt without them still validates; no gate changes."
  },
  {
   "owner": "handoffs/active/harness-program.md",
   "task_text": "- [ ] **UFH-TE-2 — Fold serving identity into the dispatch-time prepared-action recheck.** Extend the dispatch fingerprint with descriptor digest, handler artifact and config digest, serving process start time and serving tree commit. A mismatch returns `stale` and routes to re-form; stored calls are never executed silently. Acceptance: a synthetic handler swap between formation and dispatch produces `stale`, a benign restart does not, and a regression test pins both."
  },
  {
   "owner": "handoffs/active/harness-program.md",
   "task_text": "- [ ] **UFH-TE-3 — Declare admissible evidence classes for any skipped or reused call.** Write the rule that a 'safely skipped' or 'reused' claim names one of: identity receipt (the call was executed with a bound receipt), rate-tau audited population (a fraction of skips are recomputed and scored), or none. Forbid statistical language without an audited denominator. Acceptance: the rule is in the receipt contract and a lint check flags any handoff sentence that claims a skip without a class."
  },
  {
   "owner": "handoffs/active/context-and-token-economy.md",
   "task_text": "- [ ] **CTX-HO-1 — Amend CF-AB-1 A6 to the measured handoff field set and co-metric.** Replace A6's three-field schema with the seven deterministic fields (repository change state, changed source files, non-source artifacts, validation outcome, latest validation command, latest validation evidence, continuation-state label) and seven model-filled fields; add `events per solved task` beside uncached prefill as a co-metric. Acceptance: A6 text carries both field lists and both metrics; no new arm."
  },
  {
   "owner": "handoffs/active/coordination-and-churn-pipeline.md",
   "task_text": "- [ ] **CTX-HO-2 — Add a typed handoff-transfer record and ledger to the session bus.** Add a `handoff-transfer` message kind and a coordinator-owned append-only `transfers/` ledger with transfer_id, source point, base point, coverage, selected and omitted ids, budget_bytes, status, consumer, consumed_at; lazy resolution on first dispatch; ack deduped on transfer_id. Acceptance: schema, single-writer rule and a two-main fixture test."
  },
  {
   "owner": "handoffs/active/context-and-token-economy.md",
   "task_text": "- [ ] **CTX-HO-3 — Render validation evidence into the /log checkpoint envelope.** The completed-checkpoint envelope carries a `resume_state` block with the latest validation command, its observed output or exit, remaining uncertainty, a rollback note, non-source artifacts and a continuation-state label. Acceptance: a real checkpoint renders a populated block from the executed `--validation-json`; missing evidence renders as explicitly unknown."
  },
  {
   "owner": "handoffs/active/harness-program.md",
   "task_text": "- [ ] **HIL-RE-1 — Require a call-count decomposition on every token-saving claim.** Any harness token-saving figure we cite or produce must state delta calls (certified bypasses vs other), tokens/call before and after, and whether the effect is prefill or decode. A saving that cannot be decomposed this way may not be described as callback elimination. Acceptance: the reporting convention text and one worked example from intake-2652."
  },
  {
   "owner": "handoffs/active/harness-program.md",
   "task_text": "- [ ] **HIL-RE-2 — Register non-prompt reuse substrates with their invalidation sets.** One knowledge row naming per-operation graph reuse, per-action decision-graph reuse and prefix-cache reuse as distinct mechanisms, each with what invalidates it. Acceptance: the row exists and no existing reuse task is duplicated."
  },
  {
   "owner": "handoffs/active/harness-program.md",
   "task_text": "- [ ] **HIL-RE-3 — Add a telemetry read/write-asymmetry invariant for harness flags.** When a flag fires on the write side but its consumer counter is identically zero, mark it silent, exclude it from any sweep and emit one typed event. Acceptance: a synthetic unwired consumer trips the check; a clean run is silent; no inference."
  },
  {
   "owner": "handoffs/active/harness-program.md",
   "task_text": "- [ ] **HIL-RE-4 — Add an authoring-cost column to the S4 reporting contract.** Any reuse-bearing harness feature reports one-time authoring cost in dollars and engineer-hours, the break-even N against the paired baseline, whether that N is per-artefact or cross-artefact, and build cost separately from steady state. Acceptance: the S4 contract text carries the four fields."
  },
  {
   "owner": "handoffs/active/routing-program.md",
   "task_text": "- [ ] **RTG-VAR-1 — Emit a host-capability manifest as a compiled input.** Add `orchestration/host_capabilities.yaml` (CPU flags, NUMA nodes, GPU arch and VRAM, ROCm version, RAM) probed from the existing inventory scripts and consumed by the registry compiler. Acceptance: the manifest is generated reproducibly and a golden test pins its shape."
  },
  {
   "owner": "handoffs/active/routing-program.md",
   "task_text": "- [ ] **RTG-VAR-2 — Add a variant dimension to the model descriptor.** Extend the descriptor with `variants: [{quant, backend, device, path, sha256, ctx_max, measured_tps, quality_ref}]`, seeded from existing role entries and normalising the free-form quant strings. Acceptance: schema plus a migration that resolves all existing roles to at least one variant with no invented measurement."
  },
  {
   "owner": "handoffs/active/coordination-and-churn-pipeline.md",
   "task_text": "- [ ] **BUS-ID-1 — Refuse duplicate message ids in session_bus append.** `cmd_append` exits non-zero when a caller-supplied id already exists in the destination, instead of trusting it; add a regression test. Acceptance: a second append with the same explicit id fails and leaves one row."
  },
  {
   "owner": "handoffs/active/coordination-and-churn-pipeline.md",
   "task_text": "- [ ] **BUS-ID-2 — Record the unbounded-dedup invariant in BUS_PROTOCOL.** State that messages never expire, retention is cursor-gated, `--stale-after-h` labels but never drops, and a time-bounded TTL must not be introduced. Acceptance: the invariant appears with the rule number and the code references."
  },
  {
   "owner": "handoffs/active/coordination-and-churn-pipeline.md",
   "task_text": "- [ ] **BUS-ID-3 — Re-screen the R6c post-reboot brief against current rebuild_state.** Check whether rebuild now derives tokens, heartbeat task_id, leases and checkpoint fields; if so, narrow or close R6c. Acceptance: a dated screening note, not a new task."
  }
 ]
}
```
