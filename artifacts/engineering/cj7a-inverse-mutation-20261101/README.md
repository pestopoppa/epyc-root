# CJ-7a inverse-mutation fixtures

This closes the bounded CJ-7a instrument implementation. The Research repository now contains a
deterministic fixture generator and exact-format scorer under
`scripts/benchmark/inverse_mutation_v1/`. Four reversible edits use one pinned, first-party source
snapshot: arithmetic operator swap, boolean flip, off-by-one, and removed guard. Tasks contain only
fixture ID, static plain-English instruction, and mutated source. The expected inverse and source
provenance stay with the trusted scorer.

Scoring uses the existing `pass` / `fail` / `out-of-coverage` verdict vocabulary. Ruff 0.16.3 runs
isolated with line length 100, and the executable digest is pinned. Decided records include a
`decided_proposition` bound to candidate and expected normalized SHA-256 values and formatter
identity. Missing or failed comparisons carry a registered cause and leave unavailable hashes and
the proposition null. Candidate source is formatted but never executed; scoring has no model judge
or network path.

## Verification

- Sixteen focused tests passed, including all four inverse controls, wrong and unchanged mutants,
  formatting-only changes, hostile ambient Ruff configuration, source identity, actor-payload
  privacy, formatter unavailability/refusal/timeout, and undecided-proposition behavior.
- Ruff lint and format checks passed.
- The accepted bounded R6 receipt is `R6-ACCEPTED-RECEIPT.json`; its captured test process exited
  0 with a drained PID tree. It ran on CPUs 130–131 under the 34–35 prep mutex, with OMP and
  OpenBLAS set to one thread. Sampled process-tree RSS was 74,522,624 bytes over 1.836 seconds,
  below the 8 GiB and 900-second limits. The live admission snapshot recorded correctness grants
  and no conflicting timing grant. The pinned input closure was unchanged across the run.
- `native_control_proof.json` carries eight contemporaneous scorer records: four correct inverse
  controls passed and four mutated-source negative controls failed. These are model-free controls,
  not model outcomes.

## Pins and limits

The first-party source is `scripts/benchmark/e6_budget_analyze.py` at Research commit
`ba4a037de79e282940dbdc1901646e774e9939ba`, SHA-256
`844301cb9ac6a7b4344266a8a5025e7abcf47f06da27df54d6a1e675a02ad86a`, under the repository MIT
license. Source metadata and the native control receipts are included beside this note. The
implementation was published to Research `origin/main` at `3821458c9b70` (four CJ-7a commits plus
the normal merge of two intervening upstream commits).

This suite measures **mechanical edit application only**. It does not measure software engineering,
general coding ability, or model efficacy. Four fixtures do not reproduce the author's costed
60-task suite. The source caveat remains: about 6/106 published tasks fell into the named
“representative” categories; no representative-mix claim is made here. No external dataset was
imported. Prospective write-side belief capture is separately enrolled as
`VB-CJ7A-INVERSE-MUTATION-WRITE`; it must be completed before model-evaluation outcomes are recorded.

