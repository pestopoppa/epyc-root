# E8 Quality Source/Protocol Amendment Decision

**Decision required:** approve the semantic scorer repair and deterministic active-pool replay before E8 protocol ratification.

The fixed T2=500 draw contains `real_suite_v1_0043` and `needle_039`. Both have `exact_match` with `extract_pattern: \\d+`, which has zero capture groups. The active scorer contract requires exactly one, so the runner correctly fails before emitting a protocol proposal.

1. **Approve the semantic-only repair (recommended).** Change both authoritative source rows to `'(\\d+)'`, deterministically replay those two fields into the banked active `benchmarks/prompts/question_pool.jsonl`, and accept only a candidate where the two pool rows change solely in `scoring_config.extract_pattern` and metadata changes solely in `generated_at`. This preserves IDs, prompts, expected answers, scorer method, and the T2=500 denominator. Cost: one reviewed human transaction. Risk: the script stops on any active-pool pre-state or unrelated-diff mismatch.
2. **Keep the current source unchanged.** No source risk or work, but E8 remains blocked and no receipt can be minted.
3. **Redesign the T2 instrument to exclude the two rows.** Avoids amending historical sources, but changes the accepted T2=500 selection and requires a separate protocol design/review. Higher comparability and schedule cost.

**Recommendation:** option 1. The target values remain semantically identical under extraction; adding one capture group only adapts two invalid source configurations to the already-pinned scorer contract.

**Default:** option 2. Without `--attest AMEND-E8-QUALITY-SCORER-SOURCE-20260726`, the script makes no change.

**Operator commands:**

```bash
bash artifacts/operator/amend_e8_quality_source_protocol_20260726.sh --validate-only
bash artifacts/operator/amend_e8_quality_source_protocol_20260726.sh --attest AMEND-E8-QUALITY-SCORER-SOURCE-20260726
bash artifacts/operator/amend_e8_quality_source_protocol_20260726.sh \
  --recover /absolute/canonical/transaction/path \
  --attest RECOVER-E8-QUALITY-SOURCE-20260726
```

The live pool is byte-identical to
`benchmarks/prompts/pool_rebuild_a3_20260721/question_pool.activated.jsonl`.
Per the 2026-07-27 deterministic-replay policy, the transaction streams that
banked active pool and changes only the two fields sourced from the repaired
authoritative YAML rows. It does not rebuild against the mutable full registry
or cache population: those inputs have evolved since activation and would add
846 unrelated rows. The staged replay writes a durable witness, while the
transaction's exact-diff validator remains the acceptance boundary.

The reviewed wrapper is the detached integrity root: it pins the exact SHA-256
of the separate proposal manifest before any mode runs. To avoid an impossible
hash cycle, the manifest intentionally omits the wrapper and instead binds every
downstream executable/support artifact: transaction helper, pool regenerator,
this decision, and executable tests. Manifest overrides and digest overrides
are accepted only in explicit test mode with a non-production root.

The separate proposal manifest
`artifacts/operator/e8_quality_source_protocol_amendment_manifest_20260726.json`
pins all three repository heads; the pre-state hashes for both YAML sources,
the active pool, historical pool builder/witness, and E8 runner; and the hashes of this decision,
the transaction helper, pool regenerator, and executable tests. The reviewed
operator wrapper is the detached integrity root and pins the manifest hash.

The attested path locks the reviewed script inode, records durable backups and
a transaction journal, and performs an immediately-before-replace hash CAS for
each atomic file replacement. Failure rollback also uses CAS: it restores only
a file that still matches the transaction candidate and leaves a concurrent
edit untouched with `manual_recovery_required` in the journal. After the
deterministic active-pool replay, the transaction rejects changes beyond the two
specified fields and pool `generated_at`. Its final postcheck requires the exact
proposal schema, E8 era, protocol ID, T2 n=500, both repaired IDs and expected
answers, and candidate-derived dataset/scoring/vector hashes.

If the process stops after an atomic replacement but before the journal can set
`applied: true`, the locked `--recover` path validates the immutable journal
schema, canonical transaction directory, exact authoritative destinations,
in-transaction backup paths, and pre/candidate hashes. It then infers applied
state from the candidate hash and performs the same CAS rollback. A destination
that no longer matches the candidate is never overwritten; recovery exits
nonzero and persists `manual_recovery_required`.
