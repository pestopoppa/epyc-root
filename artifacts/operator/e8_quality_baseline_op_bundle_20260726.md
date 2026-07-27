# E8 Quality Baseline Reseed

**Decision required after the E8 numeric rerun reaches 16/16:** authorize the
canonical T2=500 quality baseline or defer. This is a new E8 instrument, not an
E7-matching or cross-era comparison; its workload differs from the historical E7
n=50 prior.

## Required sequence and boundaries

1. After the numeric rerun is 16/16, pause or stop AutoPilot before quality collection.
   The numeric rerun is not a substitute for the dedicated quality instrument.
   **Speed terminalization decision:** run the separately attested
   `terminalize_e8_speed_frontier_20260727.sh` only after reviewing its
   validate-only replay. It snapshots the journal-fold E8 frontier and clears the
   speed marker without dispatching trial 1459; it does not alter quality state.
2. Complete the separate human source-amendment decision and transaction. It repairs the
   two invalid zero-capture-group scorer configurations and regenerates the fixed source
   pool; without it, no E8 protocol proposal can be validly ratified.
3. Ratify the E8 T2=500 quality protocol. The ratification pins the
   source, vectors, runner, topology, and frozen-v8 provenance, but does not collect data
   or modify AutoPilot state.
4. Execute and validate the dedicated evidence: three independent repetitions for T1 and
   T2. The runner is evidence-only and cannot write baseline state.
5. Prepare a separate human-only atomic baseline-state apply transaction, review that
   transaction and the sealed evidence, then decide whether to apply it. The quality hold
   remains open until this distinct apply decision succeeds.

## Options

1. **T2=500 full-tier baseline (recommended).** Three independent 500-question T2
   observations, alongside three T1 repetitions. This is the canonical EvalTower T2 size
   and gives the strongest E8-only baseline, at the highest collection cost.
2. **Defer the quality reseed.** Do not ratify or execute the protocol. This has no
   collection cost and preserves the fail-closed hold, but E8 quality-gated decisions
   remain unavailable.

**Recommendation:** option 1, T2=500. It provides an appropriately precise E8 baseline
without claiming comparability to the E7 n=50 prior.

**Default:** option 2. Without the human source amendment and an explicit protocol
ratification, no quality evidence is collected and no baseline state changes.
