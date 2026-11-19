# CMP-3 post-fold semantic check

This explicit replay check asks whether the **actual generation request at the
forced compaction boundary** preserves the operative meaning of each six-field
execution brief and pinned governance rule. The original source, candidate
patch, runtime flags, online prompt bytes, and sealed CMP-3 packets retain their
existing custody. A semantic check runs only when explicitly requested.

The rubric asks the judge to read the complete post-fold request (including
the folded history or manifest and retained turns), preserve conditions and
scope, and identify material conflicts or missing support. A field that asserts
external state, such as the location of a record in the REPL, requires an
independent observation in the request. The rubric allows an accurate paraphrase
and distinguishes quoted context from active instructions.

The instrument preserves the independent literal delivery boolean and the
evaluator's seven judgments. It marks a case contradicted when any supported
field verdict is contradicted, entailed when all seven field verdicts are
entailed, and unknown otherwise. A missing evaluator, incomplete evidence,
malformed response, mismatched request binding, or invented citation yields
UNKNOWN. Each supplied citation is verified against the captured observation and
stored with its Unicode character span. The evaluator supplies the semantic
labels and rationale. The importer verifies structure and custody.

## Offline access

Use the sealed live ledger and its filed SHA-256 to export the four captured
contract-on continuations and the exact judge messages:

```bash
python3 -B scripts/experiments/toc-cmp-3-semantic/semantic.py export \
  /mnt/raid0/llm/tmp/delegation-context-preassembly/cmp3-live-r3/native/RESULT.json \
  6c566398cd6e36790c5f81bbd6b58e0321f3686869ddebafca27123aca4d6f08 > eval-cases.json
jq '.[0]' eval-cases.json > eval-case.json
python3 -B scripts/experiments/toc-cmp-3-semantic/semantic.py import eval-case.json \
  --evaluator-id '<reviewer or sealed model invocation>' --response evaluator-output.json
```

The export result includes exact observed message content and expected brief
and governance parsed from their original length-framed bytes. The response file
contains the evaluator's raw JSON answer, rather than the HTTP wrapper. Omit the
evaluator and response arguments to inspect the explicit unknown result.

## Isolated evaluator screen

`python3 -B scripts/experiments/toc-cmp-3-semantic/prepare.py` stages a sealed
packet under `/mnt/raid0/llm/tmp/delegation-context-preassembly/cmp3-semantic`.
Preparation uses the original live ledger, the preverified CMP-3 probe model
identity, and exact runtime binary/library digests. It does not hash the model
weights again or start a model. The packet is independently verifiable via its
`runner.py verify`. The owning session publishes its `packet/spec.json` through
rowflow. Retained native evidence includes the exact prepared packet, raw judge
requests and responses, matched Unicode spans, per-control labels, and partial
results when applicable.

The fixed matrix is three controls (meaning-preserving paraphrase, intact frame
with an active contradictory folded instruction, and missing completion
restriction), followed by four original contract-on requests (two tasks, two
arms). One private Qwen3-4B-Instruct-2507 Q8_0 judge call per unit uses four
allocator-assigned physical cores, 16,384 context tokens, a 2,048-token output
cap, at most 270 seconds per call and a 2,100-second run bound. The judge model
uses a separate checkpoint from the capture worker, Qwen3.6-35B-A3B-MTP Q8_0.
The boundary worker's answer and correctness labels are excluded from judge input. The
official row ends at seven completed units or on the first calibration failure,
transport, custody or protocol error, allocator STOP or deadline. Failed
calibration leaves native semantic outcomes unknown. A well-formed UNKNOWN on
an original request is an observed judge outcome. There are no automatic
retries. A separate publisher smoke covers the contradictory fold control and
private evaluator cleanup.

Higher correctly classified calibration coverage is better. On the four
captured requests, report field and case counts descriptively, including
UNKNOWN. One case moves a whole-capture fraction by 0.25. The completion
predicate certifies coverage, and the fixed controls provide a local
calibration check. Neither supports a model-understanding, worker-compliance,
effect-size, population, runtime enforcement or production-tenant finding.
Runtime enforcement and production-tenant validation remain separate work.
