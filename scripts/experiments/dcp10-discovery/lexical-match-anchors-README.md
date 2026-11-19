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
was removed after export. The candidate metadata records the source and test evidence.
[Source and test evidence](../../../docs/research/dcp10-lexical-match-anchors-candidate-20261118.json)

## Nine-task replay

The pinned replay reproduced the original 72 candidate records and 27 pack plans before comparing
the patched application on the same task bases and issue statements. The patch changed ten
Python candidates from whole-file fallback to AST slices. All ten first matches were on lines
1–4. Across the nine tasks, the original and patched packs contained the following totals.

| Estimated budget per task | Included files, original → patched | Gold files, original → patched | Gold lines, original → patched |
| ---: | ---: | ---: | ---: |
| 2,000 | 0 → 5 | 0 → 3 | 0 → 0 |
| 4,000 | 1 → 9 | 0 → 3 | 0 → 0 |
| 8,000 | 4 → 14 | 0 → 3 | 0 → 0 |

Lexical scores, padded previews, and C and C++ pack plans matched the baseline. The three recovered
gold files were in the xarray and Astropy tasks. Their packed spans missed the annotated lines.
All nine tasks produced discovery candidates in both arms, with zero failures or replacements.
Empty packs remained in each nine-task denominator. At 2k, 4k and 8k, their counts went from
9, 8 and 6 in the original to 7, 6 and 4 in the candidate.
The retained run is a local diagnostic with the original writable-ancestor capture refusal and
trusted packer identity mismatch.
[Per-task spans, cost estimates and render hashes](../../../docs/research/dcp10-lexical-match-anchors-replay-20261118.json)

To reproduce the comparison, apply the patch to a new detached checkout as described above.
Set `scratch` to the parent of the three retained shard directories, `candidate` to the patched
checkout, and `python` to the original app interpreter. Choose new paths for both output files
inside `scratch`, outside the retained shard directories.

```bash
runner=scripts/experiments/dcp10-discovery/replay_match_anchors.py
seal=$("$python" -I -B "$runner" "$scratch" seal "$candidate" "$scratch/replay-request.json")
"$python" -I -B "$runner" "$scratch" run "$candidate" "$scratch/replay-request.json" \
  --request-sha "$seal" --output "$scratch/replay-result.json"
```

## Current-source port

The [current-source patch](lexical-match-anchors-current.patch) applies at orchestrator
`52db82df557ce1ef22b7c9c05f2a0ce9e5f6c8b8`. Its four patched files match the replay candidate
byte for byte. The detached port passed 130 focused mock tests and Ruff. Application integration
remains with the orchestrator owner.
[Current port and test evidence](../../../docs/research/dcp10-lexical-match-anchors-current-port-20261118.json)
