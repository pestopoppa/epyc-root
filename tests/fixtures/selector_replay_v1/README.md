# Selector replay fixture

This four-decision graph is synthetic. The journal records incumbent choices;
the graph supplies predecision features for three candidate parents; the outcome
file supplies an independently recorded paired continuation for each candidate.
The final two decisions form a later time holdout. One development continuation
is a recorded evaluator failure, so the receipt must retain it in the denominator.

The fixture proves only the freezer, replay, stop logic, and VB-DGM-1 receipt
contract. Its numbers are not evidence for a production selector change.

Run from the root repository:

```bash
python3 scripts/research/selector_replay.py freeze \
  tests/fixtures/selector_replay_v1/source.json /tmp/selector-fixture-package
python3 scripts/research/selector_replay.py replay-both \
  /tmp/selector-fixture-package /tmp/selector-fixture-results
```

The current, score-only, Shinka, DGM, and HGM formulas are sealed in the package
manifest. The finalized receipt schema fixes those five arm names, so rank and
weighted Shinka are separate sealed runs over one frozen package. The
`aggregate-index.json` binds both receipts, diagnostics, raw outputs, and the
shared package digest. Rank Shinka
samples from rank^-alpha with alpha=1. Weighted Shinka samples from
sigmoid(lambda*(score-median)/max(MAD,1e-6))/(1+offspring) with lambda=10.
The source profile and RNG seed are explicit. DGM consumes source-supplied
precomputed g_D values with pinned kappa_D and valid-child rule; the runner
does not invent g_D or claim this exponent form is canonical DGM. HGM takes
seeded Beta Thompson draws from predecision
descendant outcomes, mapped to [0,1], with pinned fractional-success pseudo
descendants and prior. All are local diagnostic treatments; the fixture cannot
establish paper fidelity or real selector gain. A future feature timestamp,
missing candidate menu, missing paired outcome, or insufficient holdout
clusters causes refusal.

Historical EPYC journal shards can be frozen and audited with:

```bash
python3 scripts/research/selector_replay.py audit-historical \
  /workspace/repos/epyc-orchestrator/orchestration/autopilot_journal.jsonl \
  /workspace/repos/epyc-orchestrator/orchestration/autopilot_journal_1.jsonl \
  --expected-inventory tests/fixtures/selector_replay_v1/historical_inventory.json \
  --package /tmp/selector-historical-audit \
  --output /tmp/selector-historical-audit/audit.json
python3 scripts/research/selector_replay.py verify-audit \
  /tmp/selector-historical-audit/audit.json
```

`audit-historical` exits 2 for the expected `not_evaluable` disposition. It
writes `audit.json` first, then `missing-fields.jsonl` and a producer-sealed
`research-screen.json` in the same package. Each absent field has one `invalid`
row, with all rows in the denominator. The receipt uses the pinned inventory
as its input manifest and provenance artifact, the immutable audit JSON as its
conformance artifact, a deterministic holdout-inapplicable rationale, and a
`mechanism_feasibility` claim of `replay_evidence_completeness=0`. It grants no
promotion authority. The receipt is deliberately outside the audit self-hash.

The audit self-hash binds the pinned inventory, both full byte copies, summary,
and missing fields. `verify-audit` rechecks the audit and, when present, the
receipt and raw missing-field rows. The inventory
pins the 18,257,825 and 19,801,823 raw bytes and their SHA-256 digests. The
audit checks the 393 sequential rows, 141 candidates, 22 parent pointers that
leave the sequential subset but resolve in the full journals, and the 30,240
question outcomes with 3,514 distinct qids. Their recorded trial outcomes
do not provide an eligible parent menu or paired unchosen-parent continuation,
and model/decoding identities are absent, so the audit emits `not_evaluable`
and refuses to emit a historical **selector effect** receipt. Derived menus, edges, or
holdouts are never represented as observed evidence.
