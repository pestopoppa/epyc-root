# DRAFT — human-only same-day trash disposition ratification

This is a proposed ratification script, not policy and not authorization. Only
the operator can amend retention policy or ratify an exception. The normal
seven-day hold remains in force until a human makes and records a decision.

Proposed operator text to adopt, reject, or edit:

> For an individually enumerated set of entries that guarded_rm moved to
> trash today, an operator may record same-day approval of permanent disposal.
> Approval must identify the exact trash paths and their source paths, inode
> identities, manifest digest, date in UTC, and operator decision reference.
> A dedicated sweep may remove only those entries after confirming the record,
> audit trail, identities and no KEEP or other applicable custody constraint.
> Any mismatch, extra child, partial failure or uncertainty stops the sweep;
> an interrupted sweep is reconciled manually and never automatically retried.
> This authority does not waive retention for unrelated paths or future days.

Implementation and tests must be reviewed separately after a human ratifies
the wording. This draft does not modify trash-sweep or issue an approval.
