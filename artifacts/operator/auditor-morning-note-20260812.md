# Auditor morning note — 2026-08-12 (three operator items, one page)

**For**: the wake-up sitting · **Author**: `auditor` (coordinator ask, overnight batch) ·
Each item has its full evidence artifact; this page is the decision surface.

## 1. C39 signer — parked, two known defects, v3 ready

Full note: [`c39-signer-consolidated-note-20260812.md`](c39-signer-consolidated-note-20260812.md).
One paragraph: the e8-v4 ratifier can mint a signature without the C39 keyed receipt. Defect 1
(auditor review): a guard keyed on receipt-or-index *alone* waves through the crash-between-writes
cleaned world — a twice-mintable signature. Defect 2 (idiom **proposed** by mainA in a handover,
independently lifted into a patch by mainD, both transplants caught by the auditor): hard
refuse-on-index-exists is a one-shot idiom that would break this vehicle, whose re-run-after-crash
is the designed recovery. v3 (`e8v4_keyed_receipt_20260812.patch` @ `51738208`) fixes both,
sandbox-validated, **not applied**. mainD's draft reverted at their own insistence.
**Decision: apply v3 — or see item 3, which may moot it.**

## 2. KVQuant on the 27B — adopt / keep / rerun

Full package: [`docs/reviews/kvquant-27b-decision-package-20260812.md`](../../docs/reviews/kvquant-27b-decision-package-20260812.md).
One paragraph: exact retrieval parity f16 = q8 = q4_0 (51/52 each, the single miss is the same
item on all three arms including f16, to 200K depth); `q4_0/q4_0` buys **10.54 GiB VRAM** at
262K ctx for −7.4% decode, against a measured 1.40 GiB steady-state spare. q8 is dominated
(slower than q4_0). Observation-grade: single run, no protocol id, retrieval ≠ generation
quality. **Recommendation: A — adopt q4_0/q4_0 for `architect_general`, name what the 10.5 GiB
buys in the same change, fold a one-off reasoning spot-check into adoption.** Arm C (mixed KV)
never ran comparably; it is not evidence against mixing.

## 3. E8 final-c1 — retire recommendation (new tonight)

The token `ATTEST-E8-CONTEXT-FEASIBILITY-AND-BASELINE-APPLY-20260727` is **unspent since
07-27** — neither its context-apply nor state-apply receipt exists on disk. Its vehicle
(`ratify_and_apply_e8_quality_baseline_v4_20260727.sh`) is the **single remaining
MISSING-WRITE** in `check_ratifier_receipt_contract.sh` — the only reason the trust-boundary
conformance checker exits 1 today.

Supersession chain, verified in artifacts: the v4 candidate it would apply was superseded by
the **v5 partial-r2 final-c1** runs (capacityfix + deterministic completion, 2026-07-29), and
the cpu_bench instrument era then advanced **E8 → E9 under your signature** (2026-08-11
22:15Z). A rollback to v8/E8 would not resurrect the need: it would mint fresh evidence, not
re-apply a 07-27 candidate.

- **(a) RETIRE the token (recommended)** — mark it withdrawn in the token queue with a dated
  note (human-only act; no agent touches it). Closes the last MISSING-WRITE **without editing a
  signing vehicle at all** — strictly safer than patching; the checker goes fully green; v3
  stays on file as the template for any future re-runnable vehicle.
- **(b) Keep + apply v3** — only if you intend ever to sign the 07-27 apply, which the v5
  final-c1 completion makes moot.
- **(c) Status quo** — worst option: a permanently red trust checker trains everyone to ignore
  it, which is precisely the refuse-into-a-void failure documented tonight
  (flurry-audit addendum, "Gates that can refuse into a void").

If (a): item 1's v3 apply becomes optional rather than pending — the defect class is real, but
its only live instance retires with the token.

## Related, already in your sitting (pointers only)

E8 retire ruling context (msg-177) · reconciliation land, root + research (research is 10/136
diverged; mains' side backed up on `wrapup/research-mains-20260812`) · DAR L489 ·
execution-gate adjudication · OD-1/OD-2 · mainA's new goodput-vs-rate era-boundary filing
(w3d, 231/1372 zero-quality frontier rows) · the unwatched-gates table (flurry-audit addendum) —
headline: `check_ratification_receipts.py`, guarding the measurement boundary, orphaned since
08-02 with zero references.
