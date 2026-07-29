# E8 Context Feasibility Amendment Decision

## Observed Preflight

Read-only v4 coverage scanned all 50 T1 and 500 T2 fixed-vector rows against
the live frontdoor chat template and 32,768-token context.  It found 16 rows
that cannot be admitted: one T1 row and fifteen T2 rows.  Each qid occurs once;
there is no duplicate T1/T2 occurrence.  The complete report
is `e8_quality_context_coverage_v4_r2_20260727.json`, SHA-256
`7ef88865c5aa7315143b19cc3d40c153c59e981db7eba9bcbb2ab6ea774fe983`.

The known T1 LongBench request is independently attested by llama-server as
62,515 admitted tokens.  The live `/tokenize` helper reports 33,830 for its
rendered prompt, so the v4 runner binds the server observation for that stable
qid and otherwise uses live server tokenization.  The related failed-run
classification and checksum ledger remain immutable predecessor evidence.

## Decision Package

### Option A -- capacity-qualified replacement map (recommended)

Approve a reviewed, explicit 16-row source-vector replacement map with a
human-attested, source-pool-tier relaxation.  The map must preserve `n=50` and
`n=500`, membership tier (T1/T2), suite, scoring contract, and every old/new
qid; it must record every source-pool-tier delta and pass the v4 all-five-live-
frontdoor coverage scan before it can be applied.  The consolidated operator
transaction then writes the v4 successor receipt, collects fresh E8 evidence,
and applies baseline state only after terminal clean evidence.

Tradeoff: preserves the ratified sample counts and makes collection runnable,
but changes the quality source vector and relaxes source-pool difficulty tier.
The same-tier constraint is infeasible for the tier-3 Needle rows at the
32,768-token frontdoor, so the relaxation must remain conspicuous in the
receipt and operator attestation.

### Option B -- amend T2 size or sampling rule

Replace the 500-item fixed vector with a smaller or filtered vector.

Tradeoff: fewer source substitutions, but changes the ratified T2 count and
precision contract.  It requires a new protocol decision and is not compatible
with the current E8 T2=500 requirement.

### Option C -- expand the frontdoor context/lineup

Raise context capacity so the existing vector can run unchanged.

Tradeoff: preserves the vector, but is a production lineup/configuration
change with residency and performance consequences.  It is outside this
measurement-only repair.

### Option D -- defer (default)

Keep the current source vector and do not collect or apply E8 quality baseline
state.

Tradeoff: no source-vector change and no deployment risk, but E8 quality
baseline remains blocked.

## Consolidated Transaction Contract

The eventual one-token wrapper must, in one fail-closed transaction:

1. Validate the operator-attested reviewed replacement map and all predecessor
   hashes.
2. Atomically stage and validate the source amendment; it must not change the
   production lineup, `MEASUREMENT.md`, or instrument-era state.
3. Run the v4 full T1/T2 context preflight and mint the v4 successor receipt
   only when every row fits.
4. Run fresh `--prepare` then `--execute`; preserve all terminal evidence on
   any failure.
5. Invoke the existing evidence-bound baseline-state apply transaction only
   after all terminal evidence acceptance checks pass.

Any failure before step 5 leaves baseline state unchanged.  This document is a
review-only decision bundle, not a ratification or source-vector amendment.
