# CMP4 prospective boundary-terminal eligibility proposal

Status: **proposed; operator approval pending**. This document does not amend the
[registered protocol](toc-cmp-4-preregistration-20261109.md#7a-validity-rule-boundary-not-reached).
It applies only to a separately sealed successor if approved. Existing r3 evidence,
counts and eligibility remain unchanged.

## Proposed addition to §7a

A verified trajectory that terminates on its assigned compaction boundary has no
post-boundary action denominator. Its BAPS remains UNKNOWN, never zero. If any
scheduled arm/repeat produces this outcome, exclude the whole paired point across
all arms and repeats, and replace it with the next point in the existing seeded
reserve of the same stratum. Keep the original frozen point-list digest and record
every exclusion and replacement separately. Reserve exhaustion leaves coverage
incomplete; it does not authorize a new draw or a relaxed completion predicate.

Apply this rule only after validating native trajectory identity, the assigned
boundary, contiguous turns through that boundary, matching terminal state and
action outcome, and complete successful generation transport (or the separately
verified no-generation path). An incomplete response or malformed trajectory
continues through the existing retry/drop policy. A measured BAPS of zero remains
eligible. Neither UNKNOWN classification nor exclusion implies success or failure.

Retain the triggering arm/repeat, explicit exclusion reason, native trajectory and
graph custody, independent accuracy grade, and all earlier observations at that
point. Exclusions do not consume the transport-failure drop allowance. Report
exclusions by stratum and triggering arm, alongside replacement and reserve counts.
Exclude the whole point from paired BAPS, accuracy and Pass^3 analysis; independently
captured accuracy remains available as descriptive evidence with its own denominator.

## Interpretation and decision

Lower BAPS is better. This rule changes which points enter the comparison: final
paired results describe the retained points with observed post-boundary actions in
every scheduled arm/repeat. Termination can depend on the arm and sampling outcome,
so this is selection after treatment. The result cannot establish an unbiased arm
effect over the original pool, or identify a population of tasks that would always
continue under every arm. The early-only pilot remains diagnostic and cannot
establish all-strata efficacy or the registered MDE.

The recommended choice is prospective replacement for a diagnostic successor,
with these interpretation limits explicit. The alternative keeps §7a unchanged
and retains terminal outcomes as UNKNOWN without new replacements; the current
96-eligible-run completion predicate may then remain unattainable. Without an
operator decision, the candidate stays off and no r4 input preparation, publication
or inference is authorized by this proposal.

An approved successor must seal the eligibility policy and candidate source
identity in its inputs and run receipt; resume must reject a policy change. The
publisher's smoke still must pass before official inference. Approval of this
proposal supplies no behavioral result and does not complete parent TOC-CMP-4.
