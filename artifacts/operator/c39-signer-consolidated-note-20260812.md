# C39 signer patch — consolidated morning note (2026-08-12)

**For**: operator sitting · **Author**: `auditor` (coordinator ask, msg-134: "the two defects,
the corrected design, and who proposed what — no patch, no command") · **State**: iteration
PARKED per coordinator; one canonical artifact exists, validated, **NOT applied**.

## What this is

The e8-v4 ratifier (`apply_final` path) can mint an operator signature without writing the C39
keyed receipt index — the one residual `scripts/operator/check_ratifier_receipt_contract.sh`
exits 1 on today, by design. Three agents converged on a repair vehicle for it overnight; the
convergence found two real defects that a single author would have shipped.

## The two defects

1. **Guard-on-index-alone misses the cleaned-world crash window** *(found by the auditor's
   review of mainD's draft — and the mirror form existed in the auditor's own v2)*. A crash
   between the receipt write and the index write, followed by transaction cleanup, leaves a
   world with a receipt but no index (or vice versa) and no transaction state. A guard keyed on
   either artifact alone waves the re-apply through: **a signature that could be minted twice.**
2. **Hard refuse-on-index-exists would have broken this host** *(idiom PROPOSED by mainA in a
   handover; independently lifted into a patch by mainD; BOTH transplants caught by the
   auditor)*. The refusal was copied from the one-shot era ratifiers — but this vehicle's
   `mint_receipt` is verify-or-continue, and **re-run-after-crash is its designed recovery
   path**. A one-shot idiom in a re-runnable vehicle blocks the legitimate recovery route.

## The corrected design (v3)

`artifacts/operator/e8v4_keyed_receipt_20260812.patch`, committed `51738208`, sha256
`de56da044a64e61eaac5578ea1aeaffbb70ff0686c4fd80aad7156071c101865`. Widened durable guard —
refuse only when **(receipt OR keyed index) exists AND no transaction state is on disk** — plus
an idempotent verify-or-write `mint_receipt_index()` with hard-link exclusive publish (mainD's
exclusive-create idea, retained in a better form, with credit). Sandbox-validated on six paths;
`git apply --check` clean; independently re-verified by mainD before withdrawing their draft
(digest match confirmed). mainD's own draft is reverted at `9ec9da54` and **that revert stands
at mainD's insistence** — reinstating a first draft because it was first would discard three
readers' findings.

## Who did what (exact, per the participants' own corrections)

- **mainD** authored the first patch; later argued *against* reinstating it ("would ship a
  signer with TWO known defects").
- **auditor** reviewed rather than re-authored (coordinator's routing choice, on mainD's own
  recommendation); found defect 1 in both prior designs; assembled v3.
- **mainA** did *not* find defect 2 — they **proposed** the defective idiom in a handover,
  acknowledged it unprompted, and contributed the acceptance criterion that survived: *test the
  refusal half*, because the conformance checker greps for the write and a patch could exit 0
  while leaving the token re-spendable.

**The durable lesson** (recorded in fleet memory in this corrected form): two experienced
agents independently transplanted the same proven block into a vehicle with a different
lifecycle, within the same hour — and one reader caught both. That is a claim about
idiom-transplant across lifecycles, not about any author's care.

## Decision before you

Apply v3, or rule otherwise. The apply step and its verification commands are already queued as
their own sitting item (msg from the `51738208` handover); this note deliberately carries
neither patch content nor commands. Related standing item: the E8 retire ruling (msg-177)
determines whether the e8-v4 residual is instead retired outright.
