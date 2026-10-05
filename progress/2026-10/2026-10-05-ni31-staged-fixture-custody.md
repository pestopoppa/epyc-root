# NI05-31 — staged native source-fixture custody

The canonical `NI-CI-FIXTURE-CUSTODY` task requires an exact-byte, original
source/request/readset-bound correction for two copied public fixtures, with
secret/edit negative controls. MAIN accepted the isolated source and selected
fixture gates. Production integration and restoration of the complete original
public custody bundle remain MAIN's separate boundary; this note does not mark
that restoration complete.

Source commit `4cc17080c6209e5d7f2a744807c9cf87ae0bf70f` changes only the PII
hook's staged-loop integration, the adjacent stdlib provenance helper and its
actual Git-index tests. The helper recognizes only the reviewed redactor and
book-search source-relative path/SHA pairs at app revisions
`def18591f813070a20906f9d228ddd9dd0da9fd3` and
`4244e72b2aa8aae9a92f684fcd5090a852223888`. Unknown or changed identities undergo
the ordinary scanner. Complete indexed regular bytes are exclusively
materialized and verified through the existing native receipt reader, with
one batch Git reader and a per-phase cache. Worktree bytes cannot rescue an
invalid partial stage. Missing, malformed, duplicate, traversing or unbound
custody falls back to the ordinary scan. No scanner expression, vendor
placeholder list, producer, reader, grading rule or measurement policy changed.

The three tested source-file SHA-256 values are:

- `scripts/hooks/fixture_snapshot_provenance.py`: `32573ed6d42b3167a4ebb823882c9e673a7fd307bd4c74f6f3cc68a5463ad63e`.
- `scripts/hooks/pii_precommit.sh`: `5cafb5e16ed0e14d51b4e151bc2748709018f45d68db650c9d8ce34764d26c88`.
- `scripts/hooks/tests/test_fixture_snapshot_provenance.py`: `3c07a02934722fdf0845a0279b566ed59309795938fc839a553ee0b18b3e0040`.

Original off-host run `37307260869` used source `4cc17080` and recipe
`0d64fa8706096fe6343a83a08b69139b4ca205cb`, Python 3.13 and pytest 9.1.1.
`native-ni31-fixture-custody/original-junit.xml` contains 17 passed cases,
zero failures, zero errors and zero skips. The cases exercise unchanged true
and diagnostic original capsules, index/worktree divergence, missing/symlink/
traversal/request mismatch, wrong source binding, modified known fixtures,
duplicate materialized membership despite coherent temporary resealing,
secret additions, outside paths and existing vendor-example behavior.
Adversarial resealing occurs only in temporary test copies; retained original
records are never resealed or rewritten.

The independent caller phase's original XML contains 8 passed worktree-resolution
cases, zero failures, zero errors and zero skips. Its actual PII fixture evaluation
reported false accepts at **0/21 must-block rows** and false rejects at
**0/30 must-not-block rows**. These are selected fixture observations, not field
error rates. All three real installed wrappers blocked the secret-shaped staged
input and accepted clean input: six assertions, with no absent-hook skips.
Hosted aliases pointed to the pinned root checkout and two empty disposable
sibling Git fixture repositories; no application, model, binary or production
kernel store was supplied.

Both commands were captured prospectively through the unchanged native CI writer,
with named selections, exact argv, UTC, source/recipe SHAs, allowlisted runner
facts, declared contexts/readscope and immediate immutable phase uploads.
The pre-execution input manifest binds 1,861 original input files. A read-only
hash check matched every input against the retained originals or pinned public
fixture source. All 71 downloaded new artifact files were retained unchanged.
MAIN independently reopened both sealed receipts and their bound bytes with the
existing reader, adapter and sole shared grader: both boolean propositions are
true, command exits are zero, and both project at `Judged/Located`. This finding
adds no arbitrary production Git-index privacy warrant; `VB-PII-STAGED-WIRE`
remains the separate native gate-result write-side task.

Original evidence is retained under
`/mnt/raid0/llm/worktrees/codex-ni31-fixture-custody-validation-20261005/ni31-artifacts/`:

- `ni31-37307260869-1-fixture-custody/native-ni31-fixture-custody/receipt.json`, file SHA-256 `912b0cca071bcbc831918053db73d68aeb263e395b50c555f2cdb601d244c204`.
- `ni31-37307260869-1-caller-gates/native-ni31-caller-gates/receipt.json`, file SHA-256 `325dfa959c68f9935a40daaaf40bbe0ed0531f96ba90d521973080fcee52ae40`.

The same lane retains original command logs, XML, requests, source readsets,
contexts, input manifests and projections, plus read-only parsed summaries
`ni31-parsed-counts.json`, `ni31-caller-observations.json` and
`ni31-original-artifact-sha256.json`. Raw `ni31-run-full.log` SHA-256 is
`36e9796968475c7ced7e70fcdecf54327cad25bea4d6678cc30b7cbbb14e90ae`.
No local correctness tests, inference, API replay or full-unit replay ran.
