# P4-1 candidate validator — isolated prototype

This pure, default-disabled prototype is not connected to AutoPilot, launchers,
the registry or a strategy store. It has no production snapshot and does not
establish that a tenant exists, a digest is authentic, a policy is current,
or a lane can serve. The caller must independently authenticate the snapshot
and supply its expected fingerprint; passing two self-asserted equal strings is
not an attestation. No historical deleted stock/FF artifacts or bounds are
approved by this prototype.

Candidates contain exactly `tenant_id` and positive integer `np_slots`. The
caller supplies the serving mode, budget profile and context separately, and an
explicit reviewed tenant allowlist (empty by default). A tenant marked as
forbidding co-residency is eligible only under `solo_resident`. These injected
values are synthetic test inputs, not verified production authority.

Frontier selection follows the existing policy's smallest covering context
bucket, while requiring an exact, already-resolved budget profile and mode.
The caller must separately resolve and authenticate budget selection and reject
stale snapshots. Null, missing, duplicated and malformed entries refuse.
`trial_response.py` separately classifies a single supplied response: only an
explicit integer 2xx status without an error succeeds; all other statuses,
missing or malformed statuses, and errors refuse while preserving evidence.
It does not invoke operations, halt a trial, retry, promote or roll back. A
caller must classify every operation and enforce the lifecycle; this isolated
helper does not provide end-to-end 5xx handling.

Applying a candidate, rollback, seeding, runtime feature gating,
and actual policy integration are outside this prototype. The model-free synthetic unit tests exercise the isolated contract; owner review
and integration validation are still required.

`trial_sequence.py` is a separate default-disabled synthetic sequencing seam.
It requires an explicit, complete ordered set of callbacks, preserves classified
responses, and stops at the first failure. It neither connects those callbacks
to production nor authorizes promotion; integration must enforce the same guard
for every actual operation and revalidate policy immediately before actuation.
