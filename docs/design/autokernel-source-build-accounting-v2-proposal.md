**PROPOSED — NOT IMPLEMENTED OR APPROVED.** Current work: [AKU-06l](../../handoffs/active/autokernel-unified-surface-program.md).

# AKU-06l source/build multi-child accounting decision

## Finding

The current scheduler cannot consume the original planner, critic, and build receipts as one
selected operation. `SchedulerEngine.preview_accounting` and `account_stage` accept exactly one
`HeldClaimReceipt`; the first application consumes the issued selection and increments the
campaign attempt. Applying the second receipt is then refused. The raw child receipts also carry
their own request/stage provider identities (`setup` for actor children and `build` for the build
child), not the selected proposal's backend/stage-class identity, so relabelling one as the
selected receipt would fabricate provider evidence.

Actor `FINISH` rows retain charged seconds but not the provider receipt. Worker lifecycle retains
`TrustedHeldClaimReceipt` only in `_held_receipts` memory after the durable terminal. Thus restart
can prove that a child terminated and that actor budget was charged, but cannot reconstruct the
provider-authored resource receipt required by scheduler accounting. The source/build executor's
`_held` map has the same lifetime limit.

## Decision requested

Approve one prospective, versioned operation-child accounting route. This changes a Journal
validator and scheduler accounting semantics and is therefore HIGH even though current indexed
method impacts are small.

Recommended option: preserve every original provider receipt, bind each to the selected operation
in a controller-authored durable child record, then atomically account the closed receipt set once.
Do not synthesize an aggregate `HeldClaimReceipt`.

Rejected alternatives:

- Settling from the build receipt alone loses planner/critic cost and misstates its provider
  identity as the selected operation.
- Applying `account_stage` three times counts three attempts and consumes the selection after the
  first child.
- Summing intervals into a new receipt destroys physical-claim, device, beneficiary, and overlap
  evidence and creates facts no provider authored.
- Running the installed standalone path without settlement leaves a completed build behind an
  issued scheduler transition and must not be reported as settled.

## Minimal closed records and append order

Add `UNIFIED_DRIVER_CHILD_ACCOUNTED.v1` as a new Journal kind. It is accounting evidence only,
never execution or scientific authority. Its exact body contains campaign/config/supervisor,
catalog/transition/selection digest, operation kind, child role and ordinal, actor reservation or
source-build binding digest, exact request/plan/lineage/stage identities, terminal identity and
digest, the complete original `HeldClaimReceipt` plus digest, disposition, predecessor child
digest, and its own content digest. Roles are closed to `planner`, `critic`, and `build` for this
operation version. Unknown fields, roles, order, duplicate request/receipt IDs, or changed retries
refuse. Old readers refuse the new kind.

The controller method accepts typed live lifecycle facts and the exact object returned by
`worker_held_claim_receipt`; it accepts no caller receipt mapping. It rederives the issued
catalog/transition/selection, joins planner/critic through the existing durable actor `INTENT`, and
joins build through a new source-build `INTENT` written before child launch. It verifies worker and
grant generations, request/plan/lineage/stage, and the provider receipt.

The authoritative lifecycle order must be explicit:

1. existing `OWNED_TERMINAL` proves publishers joined, process/container gone, and claim released;
2. the provider returns the typed `TrustedHeldClaimReceipt`;
3. new `WORKER_HELD_RECEIPT.v1` durably records its complete immutable binding and original
   `HeldClaimReceipt`;
4. `WORKER_RESULT_ACCEPTED`/`WORKER_RESULT_STALE` records result disposition;
5. the operation owner appends `UNIFIED_DRIVER_CHILD_ACCOUNTED.v1` by joining the durable operation
   intent, held-proof row, and result row.

The held-proof row is accounting-only. If a crash occurs after `OWNED_TERMINAL` but before the
provider returns, or after provider return but before step 3, no durable provider cost exists:
successors are fenced and accounting remains uncertain. A crash after step 3 but before step 4 can
recover the original held cost and derive only an `accepted=False` diagnostic terminal from the
retained result/`OWNED_TERMINAL`/held rows; it cannot resurrect result or measurement authority.
A crash after step 4 but before step 5 replays the exact terminal and held proof and appends the
child row idempotently. A crash after step 5 but before final settlement reopens the ordered child
prefix. This ordering replaces the earlier ambiguous phrase “after terminal before child append”:
there are two distinct durable boundaries, and only the post-held-proof side is chargeable.

Add `UNIFIED_DRIVER_SETTLED.v2` on the existing settlement kind. It carries ordered child-record
references/digests rather than a caller-selected receipt. `CampaignController.unified_driver_settle`
reopens the indexed child records and derives their original receipts; the registered sole
execution validator checks expected roles, dispositions, terminals, and any enrollment reference.
V1 remains byte-for-byte supported for existing single-child runtime/profile/calibration records.

## Scheduler operation accounting

Add an atomic `preview_operation_accounting(selection, original_receipts, outcome)` and matching
preview application, used only by the v2 controller path and replay. It must validate all receipt
IDs/digests, collisions, per-child duration, and capacity before mutation. The controller's durable
child bindings replace only the inappropriate raw
`proposal_id/backend/stage_class == selected proposal` check; every other issued
selection/config/round/slot check remains.

Do not reuse `_check_receipt_overlaps` as a blanket multi-child rule. Exact duplicate receipt IDs
with identical content are aliases and are charged once; a reused ID with changed content refuses.
For concurrent different receipts, use only provider-authored allocation fields already present in
`HeldClaimReceipt`: overlapping CPU holds are admissible only when their affinity-core sets prove
disjoint partitions and the simultaneous physical fractions and memory reservations remain within
capacity. An overlapping GPU device is not partitionable in the current grammar and refuses.
Shared physical claim IDs without disjoint affinity evidence also refuse. A sweep over interval
endpoints must enforce aggregate capacity even when providers used different physical claim IDs.
This distinguishes duplicate charging from valid partitioned occupancy without adding a new
provider policy or treating a claim label alone as exclusivity evidence.

One operation:

- consumes the selected slot once;
- increments campaign and seed attempts once;
- stores every original receipt and one `AccountedReceipt` per original receipt, all bound to the
  same selection digest/outcome;
- adds the sum of original held durations to campaign/seed charged seconds;
- adds each receipt's original physical, GPU, memory, and beneficiary cost, and the sum of their
  normalized dominant resource terms to deficit;
- clears the issued selection only after the whole preview is durably appended and applied.

No numerical grading, build acceptance, promotion, or deletion rule changes.

`campaign_charged_seconds` and `SeedAccount.charged_seconds` remain occupancy accounting: they are
the sum of each original held interval and can exceed elapsed wall time when valid partitions run
concurrently. That matches the current single-receipt meaning and the existing `AccountingView`
`held_seconds` calculation. It is not operation latency. If elapsed wall time is later required, it
must be a separately named diagnostic (the union from earliest start through final end), and must
not silently replace the existing charged-time budget or deficit arithmetic.

## Admission, outcomes, and recovery

- A resource/admission denial before the planner starts has no held interval and no receipt. While
  the denial is retryable, the selected operation remains `waiting`; it is not settled and the same
  child is not reported as launched. Current `StageAdmission` has only `allowed` and free-text
  `reason`, so the prospective API must add a closed retryable/terminal denial classification and a
  durable negative-admission reference. Free-text must never decide accounting.
- A retryable critic/build denial after a charged prefix also remains `waiting`. Durable child rows
  prevent replaying already charged planner/critic children; only the denied next role may receive
  a new, ordered admission attempt. No prefix receipt is accounted until one atomic terminal
  settlement.
- When a classified terminal denial or the operation deadline ends retry, settle exactly once. If
  the prefix is empty, `UNIFIED_DRIVER_SETTLED.v2` references the durable negative-admission row and
  performs a no-receipt cancellation: one failed attempt, zero charged seconds, and no fabricated
  `HeldClaimReceipt`. If a prefix exists, settle `failed` with that exact prefix plus the denial
  reference, charging every prefix receipt once. This requires an explicit scheduler
  `preview_operation_cancellation` for the empty case; passing a fake zero-duration receipt remains
  forbidden.

Concretely, current `WorkerLifecycle._admit` raises `WaitingAuthority`; `_run_stage` exactly releases
the unadmitted grant and durably resolves the acquisition, but `ActorLifecycleAdapter.invoke` then
surfaces an exception and `ActorPreparationConsumer._invoke` converts it to a zero-second failed
`StageOutcome`. That row is actor-budget disposition, not scheduler cost authority. The new
`StageAdmission` denial enum and acquisition-resolution field must survive through a typed
`ActorAdmissionDenied` result. `ActorPreparationConsumer` records the reservation disposition but
must return waiting/terminal classification to the operation owner rather than treating the
zero-second actor row as a receipt. Re-admission uses a new ordered child-attempt identity under the
same selected transition; the existing finished reservation is never reinvoked.

- Planner failure: append/account the planner child only; settle `failed`.
- Critic refusal/failure: append/account planner and critic; settle `invalid` for an explicit
  refusal, otherwise `failed`; never launch build.
- Build failure/nonzero/containment failure: append/account all completed children; settle
  `failed`; enrollment is absent.
- Success: append all three child rows, verify the immutable enrollment pointer, then settle the
  selected actor operation as `prerequisite` (not a valid scientific comparison).
- Restart with a durable child row but no final settlement: never relaunch that child. Reopen the
  ordered prefix and settle diagnostic failure if the next operation capability cannot be
  reconstructed. Completed build without a durable enrollment pointer cannot be resurrected as
  success, but all durable original child costs are still charged.
- Restart with `OWNED_TERMINAL` but no durable held row: fence successors and report accounting
  uncertainty. Neither zero cost nor a reconstructed receipt is allowed.

## Exact implementation scope

- `autokernel/journal.py`: new closed child kind/validator and v2 settlement validator; preserve v1.
- `loop/worker_lifecycle.py`: closed `StageAdmission` retryability/terminal classification,
  versioned acquisition denial reference, and versioned durable held proof emission/replay before
  final result publication, restoring accounting only, never result/measurement authority.
- `loop/campaign_control.py`: child index, typed record method, replay, v1/v2 settlement derivation.
- `loop/scheduling.py`: atomic multi-receipt preview/application and explicit no-receipt terminal
  cancellation; state schema can retain existing receipt/accounted-receipt arrays, but cancellation
  needs its own durable accounted-operation identity so retry cannot masquerade as an unissued
  transition.
- `loop/actor_lifecycle.py` and `loop/source_build_execution.py`: pass typed live terminal/receipt to
  the controller at the existing ownership boundary; propagate typed negative admission without a
  fake receipt; source build writes its exact selected binding before launch.
- `loop/driver_execution.py` and `loop/standalone_runtime.py`: sole-validator delegation and only
  report `settled` after the v2 accounting event.
- Focused tests in the corresponding Journal, scheduler, controller, actor, source-build, and
  standalone modules.

GitNexus on the current index reports `SchedulerEngine.account_stage` LOW (3 direct),
`CampaignController.unified_driver_settle` LOW0, and
`WorkerLifecycle.trusted_held_claim_receipt` LOW0, but the existing Journal native payload
validator was previously measured HIGH with 20 upstream consumers. That trust-boundary result
controls; implementation remains stopped pending explicit approval.

## Required regressions

Test success and each early-failure prefix; retryable planner denial stays waiting with no receipt;
terminal planner denial performs typed no-receipt cancellation; retryable critic/build denial keeps
and does not charge/relaunch the prefix; terminal denial charges the prefix once; exact retry;
receipt reorder/duplication/substitution; same-plan different child/terminal; backend/stage
relabelling; same-ID changed-content refusal; same-ID exact alias charged once; overlapping same
claim with disjoint CPU partitions accepted within aggregate capacity; overlapping affinity/GPU or
aggregate-capacity excess refused; one attempt with three receipts; summed occupancy seconds versus
shorter elapsed wall time; exact physical/GPU/memory/beneficiary totals; crash at every boundary
from `OWNED_TERMINAL` through child append; crash after complete build before settlement; restart
replay equality; v1 replay unchanged; and an actual standalone profile→planner→critic→build chain
whose selected transition becomes `prerequisite` only after all original costs are durable.

## Main-review constraint

Receipt alias deduplication applies only after exact original child bindings agree. One receipt
cannot satisfy two distinct planner/critic/build terminals or roles. Add a negative test for
cross-role reuse even when the submitted receipt bytes and digest are identical.

