# DCP-10 lexical match anchors candidate

Apply the [candidate patch](lexical-match-anchors.patch) to a detached orchestrator checkout at
`072d1583b3ead7456731946cd4e4595da6a9877f`. The patch addresses the padded-window failure found in
the [retained cost diagnostic](../../../docs/research/dcp10-cost-diagnostic-20261118.json).

Task-root lexical search adds `lexical_match_lines` with the first body match, or an empty array for
a filename-only match. The existing score and `start_line` / `end_line` preview bounds stay intact.
Context discovery uses the explicit body match for Python AST slicing and consumes legacy hit ranges
as before when the new field is absent. It drops hits with malformed metadata. An empty anchor list
or a required anchor outside a selectable AST statement still requires the whole file, which the
packer excludes when it exceeds the budget. Codemap and content-hash checks stay in force.

The five focused test files passed 130 tests under Python 3.11.17 in mock mode. The tests cover
preview compatibility, required ranges from mixed inputs, invalid metadata, source-backed slice
rendering, and fallback for filename-only, comment, and out-of-file anchors. The detached candidate
was removed after export. Evidence is limited to the source candidate and tests.
[Source and test evidence](../../../docs/research/dcp10-lexical-match-anchors-candidate-20261118.json)
