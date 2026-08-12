# PREPARED, NOT APPLIED — C39 keyed-receipt write for the E8 v4 signer

**Prepared by `mainD`, 2026-08-12, on `coordinator-agent`'s PREPARE-AND-VALIDATE-ONLY assignment.**
This patch is **not applied**. A signing vehicle is the operator's to change; two agents already
declined to edit it and that judgement stands.

## What it fixes

`scripts/operator/check_ratifier_receipt_contract.sh` **exits 1 right now**:

    MISSING-WRITE: ratify_and_apply_e8_quality_baseline_v4_20260727.sh
                   (token=ATTEST-E8-CONTEXT-FEASIBILITY-AND-BASELINE-APPLY-20260727)

That script can mint an operator signature **without leaving a keyed receipt**. C39 fixed the
reading side — the relay cross-checks presented gates against receipts so a spent gate is flagged
rather than re-signed. This is the writing side: a signature that leaves no receipt is invisible to
that cross-check, so the gate presents as pending forever and the relay is right to say so.

## What it changes — and what it does not

- **Refuses** `--attest` if `receipts/<TOKEN>.json` already exists (a second signature is refused
  rather than minted invisibly).
- **Writes** the keyed pointer after `apply_final` returns, so a failed apply mints nothing.
- A **pointer, never a copy** — an operator signature must not acquire a second source of truth.

It changes **nothing** about what gets signed, what is validated, or when the script refuses on its
own terms. It is the 14-line block already proven in `ratify_annexg_v9_currency_20260811.sh` and
`ratify_consolidated_era_rows_20260811.sh`, copied rather than reinvented, guard wording included.

## Validation performed (and what is NOT yet proven)

- `bash -n` on the patched copy: clean.
- `git apply --check`: **clean**, applies without conflict.
- The checker's own predicate (`grep -q "artifacts/operator/receipts/"`) run against the patched
  copy: **passes** — the script would be skipped as contract-adopted. The unpatched original fails
  that same test, which is exactly why it is reported today.
- **NOT proven, and it cannot be from here:** that the checker exits 0 *afterwards*. That is only
  true once the patch is applied. The other half of the checker (`on-disk ratified receipts lacking
  a keyed index`) already reports `(none)`, so this MISSING-WRITE is the sole remaining failure and
  removing it should take the checker to 0 — stated as an expectation, not a measurement.

## The command to apply (operator)

    cd /mnt/raid0/llm/epyc-root
    git apply artifacts/operator/prepared/c39-e8v4-keyed-receipt.patch
    bash scripts/operator/check_ratifier_receipt_contract.sh; echo "exit=$?"

**Run the checker DIRECTLY, never through a pipe.** `mainA` hit exactly that trap tonight: piping to
`tail` and reading `$?` returns *tail's* status, so a script exiting 1 read as 0. I reproduced it
myself before believing it.

Expected after applying: `(none)` under both headings and **exit 0**.
