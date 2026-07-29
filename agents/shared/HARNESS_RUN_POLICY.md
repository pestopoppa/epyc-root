# Harness Run Policy

**Status:** editable template for a selected cooperating harness; not a runtime
loader, a benchmark protocol, or a replacement for the agent operating
constraints. A concrete harness must copy or reference this document by policy
identifier and revision in its realized-run disclosure.

## Policy identity and scope

- **Policy identifier:** `epyc-harness-run-policy`
- **Revision:** `2026-07-29`
- **Applies to:** a harness client that cooperates with the Orch through the
  documented `/v1` request contract and tools it has been granted.
- **Does not own:** model routing implementation, tool parsing/execution,
  sandboxing, persistence, validators, trace emission, measurement policy, or
  protected-path enforcement. Those mechanisms remain code- or human-owned.

## Run objective and authority

Complete the stated task with evidence that a reviewer can inspect. The harness
may organize work, choose among its exposed tools, and request documented
per-request overrides. It must treat the Orch's response contract, tool
permissions, approval gates, and human-only boundaries as authoritative.

When the task needs a decision outside those permissions, preserve the available
evidence, state the blocker and a concrete recommendation, and stop rather than
inventing authority.

## Required workflow

### Establish the task record

State the requested outcome, scope, constraints, and success evidence before
material work. Reuse saved artifacts and deterministic transformations where
they answer the question; do not regenerate inference merely to obtain a
different presentation of the same result.

### Plan and act within the exposed surface

Choose the smallest sequence of tool actions that can create or inspect the
needed evidence. Keep inputs, assumptions, requested overrides, and material
tool outputs attributable to the task record. A child or delegated task receives
the same policy identity plus its parent task, assigned scope, expected artifact,
and return condition.

### Verify the outcome

Use the task-appropriate static check, focused test, artifact inspection, or
review. Distinguish an observation from a decision-grade claim. Do not infer a
successful real path from a dry run, placeholder, or unrelated passing check.

### Report and stop

Return the outcome, evidence locations or commit identifiers, validation
performed, residual risks, and the next action or blocker. Stop after the
success condition, a protected boundary, an unrecoverable dependency, or an
explicit cancellation. Do not continue speculative work after a terminal
condition merely to fill context.

## Artifact and handoff contract

Every material handoff records, in a durable artifact or trace:

- policy identifier and revision, plus an explicit migration diff if changed;
- task and parent-task identity, owner, scope, and declared completion
  condition;
- inputs, constraints, assumptions, and the authority/permission posture;
- actions or artifact references sufficient to reproduce the reasoning path;
- output or decision, validation evidence, and unresolved risks; and
- recipient, return condition, and stop state for delegated work.

The receiving actor must not rely on unstated conversational context for any
required input, artifact, or authority. If required information is missing, it
reports the missing field instead of fabricating a continuation.

## Retry, escalation, and adaptation

Retry only an observable, recoverable failure with a changed input, method, or
environmental condition recorded in the task record. Escalate when a retry would
cross a permission, resource, safety, or measurement boundary, or when the
evidence is insufficient to distinguish failure from an unsupported assumption.

Model-specific adjustments belong in a separate adaptation manifest. That
manifest may set the selected model or quantization, context/token budget,
prompt wording, and documented request overrides. It must identify every
departure from this policy and must not convert an implementation detail or
unreviewed experience memory into an implicit policy rule.

## Realized-run disclosure and change control

A run report names this policy revision, the adaptation manifest revision, the
realized model/configuration, exposed tools and permissions, and the applicable
Harness Card. A model or freeze change retains this policy or supplies a
reviewable migration diff and refreshed Harness Card before it is called
re-targetable.

Policy edits are ordinary reviewable document changes. They cannot amend
human-only governance or make code-owned mechanisms optional. Any future
adherence probe may score this document against saved traces for workflow,
stage, ordering, artifact, tool-call, and handoff behavior; that probe is
separate from this template and does not itself establish model capability.
