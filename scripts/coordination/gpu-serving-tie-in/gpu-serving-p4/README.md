# P4-1 candidate validator — isolated prototype

This pure, default-disabled prototype is not connected to AutoPilot, launchers,
the registry or a strategy store. It has no production snapshot and does not
establish that a tenant exists, a digest is authentic, a policy is current,
or a lane can serve. The caller must independently authenticate the snapshot
and supply its expected fingerprint; passing two self-asserted equal strings is
not an attestation. No historical deleted stock/FF artifacts or bounds are
approved by this prototype.

Frontier selection follows the existing policy's smallest covering context
bucket, while requiring an exact, already-resolved budget profile and mode.
The caller must separately resolve and authenticate budget selection and reject
stale snapshots. Null, missing, duplicated and malformed entries refuse.
Applying a candidate, rollback, seeding, 5xx handling, runtime feature gating,
and actual policy integration are outside this prototype. The model-free
synthetic tests have not been run; the owner must review and validate before
considering integration.
