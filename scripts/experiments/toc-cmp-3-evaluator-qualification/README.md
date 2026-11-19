# CMP-3 evaluator control candidate

**PARKED: three publisher qualifications failed. Do not republish this lineage.** The source and sealed packets preserve the attempted instrument. [Observed failures](../../../docs/research/toc-cmp-3-runtime-semantic-results-20261118.md#development-calibration-follow-up) establish no qualified evaluator or production readiness.

This control-only candidate follows the [runtime and isolated semantic results](../../../docs/research/toc-cmp-3-runtime-semantic-results-20261118.md). The first 4B smoke failed on response shape and citation grounding. The r2 schema fixed the paraphrase smoke, but the 4B model still treated the repeated bank-verification assertion as independent support. The final r3 packet changes the evaluator to the receipted Qwen3.6-35B-A3B-MTP Q8_0 model and retains the r2 rubric, schema, controls, expected labels, and strict importer.

The [protocol](../../../docs/design/toc-cmp-3-evaluator-qualification-protocol-20261118.md) defines the four controls and first-failure stopping. Publisher smoke requires both the paraphrase and unsupported external-state controls to pass. These controls were reused adaptively after observed failures. A complete r3 result establishes in-sample schema and prompt calibration on these controls. Held-out or general semantic reliability requires separate evidence.

Preparation runs outside the grant:

```bash
python3 -B scripts/experiments/toc-cmp-3-evaluator-qualification/prepare.py
```

It seals the candidate and binds the CF3C input receipt, prior weight receipt, exact chat template, and pinned v10 build without rehashing weights. `semantic.py`, `cmp2_runner.py` and the linkage verifier are copied from the prior sealed packet; execute the generated packet through `publish_row.py`, rather than invoking the source runner directly. The source tests use local dependencies and mocked transport, so they require no model inference.

Native request/response bytes include the response schema and its observed-line citation choices. Strict located citations, expected and observed labels, private serving identity and cleanup remain separate artifacts. `PARTIAL.json` retains the first failed control and the unobserved remainder; it cannot satisfy the completion predicate. The r3 preparation archive retains both earlier smoke failures and their request, response, and verdict files. Candidate prompts must remain sealed after publication. Any subsequent change requires its own prospective packet and row.
