# Stage 3 Action Distillation

Use this reference during Stage 3 after the Stage-2 close-out gate has closed. It supplements the
coverage and approval rules in `SKILL.md`; it does not change the four-stage write boundaries.

## Goal

Convert the complete verified-actionable ledger into the smallest execution program that can change
an EPYC decision or produce a reusable project capability. Preserve every source row by mapping it to
an immediate packet, a trigger record, `knowledge-only`, or `decline`.

## Execution postures

### Context and opportunity before compression

For each packet, record the current EPYC objective, pinned implementation gap, smallest useful
operational change/probe, expected benefit direction, owner and exact execution conditions. Read both
implementation and documentation: a historical gap may already be repaired, while a filed enabling
task may leave its operational consumer unimplemented.

Choose an enabling primitive after this review. Reuse existing receipts, contracts, evaluators and
adapters; additional wiring needs a concrete missing capability and a consumer. Preserve distinct
operational and enabling recommendations when the source ledger distinguishes them.

For a `monitor` or `knowledge-only` closure, record which useful immediate step was considered and
why none remains. Name an observable trigger for `monitor`, or the retained contextual use for
`knowledge-only`. Nondeployment, missing full reproduction, or HIGH/CRITICAL risk alone does not
settle the opportunity. Specify safeguards and genuine execution/approval conditions, including
whether an isolated probe is permitted before production activation.

The main reviews those premises and mappings. Payload validation checks structure and evidence-field
presence; it cannot determine truth, ROI or whether wiring preserves an operational opportunity.

| Posture | Use when | Stage-3 result |
|---|---|---|
| `primitive-now` | The context review identifies a missing contract, receipt, fixture, adapter, preflight or shadow capability with a concrete consumer and immediate project value. | One owned task plus its consumer map and separately mapped operational follow-through. |
| `cheap-screen-now` | Existing records or a small controlled probe can decide whether broader work is justified. | One minimum-rigor experiment with a predeclared stop/promotion rule. |
| `full-reproduction-now` | A named escalation trigger has already fired and no cheaper probe can settle the project decision. | The smallest claim-bearing reproduction needed for that decision, with the fired trigger recorded. |
| `monitor` | No immediate work remains; an observable future condition would justify it. | Durable trigger prose with an owner; no active checkbox or index next action. |
| `knowledge-only` | The result informs architecture or methodology but creates no work or trigger. | Disposition evidence explaining its retained use. |
| `decline` | The reviewed action should be closed. | Explicit rationale. |

Several source rows may map to one primitive or screen. Record the complete mapping so compression
does not become silent deletion.

The posture labels describe Stage-3 planning. When writing intake metadata, map `knowledge-only` to
`integration_disposition: knowledge_only` and `decline` to `integration_disposition: declined`.

## Minimum viable rigor

Every immediate empirical experiment or replay has these six controls:

1. **Frozen input manifest** — identify the inputs and retain a digest or immutable revision.
2. **Current baseline** — name the production system or policy being compared.
3. **Per-item raw outputs** — retain outputs, errors, decisions, and enough identity to replay them.
4. **Holdout** — use a held-out split or a later time window that was not used to choose the method.
5. **Complete denominator** — count failures, invalids, and abstentions rather than dropping them.
6. **Predeclared decision rule** — state the stop, reject, shadow, or promotion threshold before the run.

An empirical screen missing an applicable control cannot enter the immediate program. Repair its design
in the plan, or assign `monitor` or `decline` with a reason.

This is a planning floor subordinate to `MEASUREMENT.md` and its protocols. Stronger domain rules
govern when they apply. It creates no evidence grade and authorizes no deployment.

For deterministic infrastructure, do not invent a holdout. Name the applicable conformance fixtures,
provenance bindings, mutation cases, refusal branches, or deterministic replay checks, and state why
any empirical control is inapplicable.

## Consumer discovery

Consumer completeness means identifying every presently discoverable subsystem that can use the
artifact. It does not mean duplicating its implementation task into every handoff.

For each primitive:

1. Search active and completed handoffs, experiments, registries, schemas, adapters, and implementation
   repositories for the contract, data shape, task family, and expected output.
2. Record the search terms and surfaces inspected in the plan.
3. Name one primary implementation owner.
4. Classify consumers as:
   - **direct** — calls, imports, or executes the artifact;
   - **evidence** — records or reads its receipts and outcomes;
   - **policy/evaluation** — uses its result in a gate or comparison; or
   - **prospective** — consumes it only after a named trigger fires.
5. Create a consumer-side checkbox only for distinct code, schema, migration, acceptance, or rollout
   work. Otherwise record the supported interface or dependency at the primary owner.

## Trigger quality

A broader reproduction trigger must be observable and falsifiable. Valid trigger classes include:

- a held-out cheap screen clears its predeclared improvement threshold;
- a measured project bottleneck matches the resource or failure mode the technique addresses;
- the external artifact is about to support a promotion, policy, benchmark, or authoritative claim;
- a live consumer requires behavior that the reusable primitive alone cannot provide; or
- an external result conflicts with current EPYC measurements and replay cannot resolve the conflict.

“Interesting,” “state of the art,” “promising,” and “might help later” are not triggers. An unfired
trigger is dormant, not blocked. It remains prose under an owner until a reviewed session confirms the
condition and materializes a task.

## Plan item template

```markdown
### {Plan item ID} — {Immediate project action}

- **Project decision:** {current EPYC choice, risk, bottleneck, or missing capability}
- **Pinned implementation gap:** {revision, files and current behavior; existing fulfilled work}
- **Operational opportunity:** {smallest useful change/probe and changed consumer behavior}
- **Expected benefit direction:** {what should improve and what must remain correct; no invented gain}
- **Execution conditions:** {implementation/probe/activation conditions, safeguards and actual gates}
- **Sources and ledger rows:** {complete source-to-action mapping}
- **Primary owner:** `{handoff}`
- **Execution posture:** `{primitive-now | cheap-screen-now | full-reproduction-now}`
- **Enabling primitive:** {specific missing capability, or existing artifact reused/no new primitive}
- **Operational versus enabling mappings:** {distinct recommendation IDs and their task/trigger refs}
- **Consumers:**
  - `{direct consumer}` — {interface used}
  - `{evidence or policy consumer}` — {receipt or decision use}
  - `{prospective consumer}` — {activation trigger}
- **Consumer search evidence:** {repositories, files, registries, and terms searched}
- **Immediate deliverable:** `- [ ] **{TASK-ID} — {paste-ready task line}**`
- **Frozen input:** {manifest and digest, or deterministic inapplicability reason/check}
- **Incumbent baseline:** {current production system or policy}
- **Per-item evidence:** {retained output path or schema}
- **Holdout:** {split/later window, or deterministic inapplicability reason/check}
- **Denominator:** {failure, invalid, and abstention treatment}
- **Stop/promotion rule:** {predeclared decision}
- **Dependencies and concurrency:** {critical predecessors and independent lanes}
- **Broader-reproduction trigger:** {observable condition}
- **Broader follow-on if unfired:** {owned trigger prose with no checkbox for that broader step}
- **Closure opportunity review:** {for monitor/knowledge-only, considered immediate step and grounded
  reason none remains; reference the proposed filing payload}
```

Target three to five immediate work packets when that many independent units survive compression. If
fewer remain, present fewer and state why; never split a primitive merely to reach the target. Put shared
enabling primitives before the evaluations that consume them. Show independent lanes as concurrent; if
all packets are dependency ordered, state that no safe parallel lane exists.

## Transformation examples

### Decision model paper

**Avoid:** recreate the paper's full benchmark matrix, training recipe, and seed grid because its
headline result is promising.

**Prefer:** where the pinned typed-decision path already supplies receipts and calibration, reuse
them. If existing cases prescribe the tool and cannot test operation selection, extend those cases
with a tool-choice step and compare against the current same-server REPL choice-and-arguments path.
Keep proposed versus executed actions distinct; an original action's outcome does not label an unused
alternative. Freeze inputs, retain per-case outcomes and failures, hold out tool/state families and
predeclare the decision rule. Name the permitted sidecar/window and separate activation conditions.
Broader reproduction follows only its own fired trigger.

### Evolutionary selector paper

**Avoid:** launch a new candidate-generation campaign for every published selector.

**Prefer:** identify the current selection failure and reuse the journal, candidate graph, replay
adapter and output carrier where present. Compare selectors on untouched continuation groups with
the six controls. Repair only a demonstrated adapter gap. Stop under the predeclared rule if no useful
selection improvement remains; broader reproduction needs its own deciding result or claim need.

### Specialized multimodal model

**Avoid:** download and benchmark the full model family before a relevant bottleneck exists.

**Prefer:** review the selected consumer and its current modality path first. A text-only workload
with no current visual consumer can support knowledge-only retention with that explicit rationale.
A live visual consumer with a documented bottleneck can justify a bounded comparison now, even while
deployment remains gated. Record the actual artifact/runtime conditions and six controls; keep only
the genuinely future step under an owned observable trigger.

### One owner, many consumers

**Avoid:** copy the same receipt-implementation checkbox into routing, evaluation, and evidence
handoffs for visibility.

**Prefer:** give the receipt one implementation owner, list routing and evaluation as interface
consumers, list the evidence substrate as a receipt consumer, and create separate tasks only where a
consumer needs an adapter or acceptance test.
