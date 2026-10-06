# IRV native correction-event wiring draft — main applies only after approval

The adapter is already present: `scripts/vidya/adapters/README.md:32` defines the existing `literature` ladder as source-verification status → `Verified`, owned by `research_intake.py`; line 233 lists `research/intake_index.yaml` as live and handled by that adapter. Do not add a duplicate generic intake-source row.

Proposed new README event-path row (under correction/refresh lifecycle, not source list):

| Event path | Native event records | Existing ladder | Scope |
|---|---|---|---|
| Research-intake source correction / verification refresh (`research_intake.py`) | Pinned, exact-target native retraction of stale current support/opposition. Corrected source claims receive reviewed native replacements; Stage-1 demotions retain Hinted discovery projections; administrative record-status placeholders receive no source-evidence replacement. Immutable old frames remain history. | Replacements go through the existing `literature` ladder and `claim_tuple.grade()`; no new class, score, or grading rule. | Only explicitly bound entry/claim/warrant IDs and corrected index/manifest digests; preserve unaffected sibling claims and prior refutations as dated history. |

Exact proposed handoff task ID and text (`handoffs/active/vidya-belief-substrate-program.md`):

- [ ] **VB-RI-CORRECTION-REFRESH-1 — Wire pinned research-intake correction/refresh events for graded current warrants and scoped withdrawals.** Extend the existing `research_intake.py` write path so an approved, digest-pinned correction retires only named current native support/opposition warrants and reprojects only the reviewed current source claims through the existing literature ladder. Stage-1 demotions retain Hinted discovery projections; explicitly bound administrative record-status placeholders retain their addresses and history without source-evidence warrants. Preserve immutable history, unaffected sibling warrants, and exact-ID retry after interrupted append. Validate against the approved filtered-index and warrant manifest; do not add a grading ladder or change policy.

Owner: existing Vidya substrate program. This is an event-path correction/refresh hook; it does not restate or duplicate the already-live intake adapter. Draft only, not assigned/applied.
