# DTREE winning-path prompt repair

This source-only repair replaces the pending main-draft suffix in
`slot.prompt.tokens` with the winning alternative before assigning that
alternative to `slot.spec_draft`. It preserves the prefix and sampled anchor.
The subsequent accept code can then remove the winner's length and append its
accepted tokens without changing the next position relative to committed memory.

In source `47f08e797c3dca352ebd6f7c5f80260d1e48aa90`,
`handle_last_sampled_token` appends the main draft to the prompt. Later,
`spec_tree_resolve` replaces `spec_draft` with an alternative. Finally,
`verify_and_accept` removes `n_draft`, measured from the alternative. Without
this repair, the prompt length is wrong by `main_length - winner_length`, and
even equal-length alternatives leave incorrect token contents in that suffix
until acceptance removes it. A shorter winner can produce the observed next-root
position being one greater than the committed memory expects.

The 27B P5 T12 log records root position 89, expected 88. That log lacks the
winning-path lengths, so attributing that particular runtime failure solely to
this defect remains an inference. The regression establishes the source defect
and its repair independently; it does not establish runtime correctness or speed.

Source binding: experimental llama.cpp Git object
`47f08e797c3dca352ebd6f7c5f80260d1e48aa90:tools/server/server-context.cpp`,
SHA-256 `71014850daf569637e012dd9d9a5b3b50994f44e996c2e00f98165a24767beb3`.
`port.py` refuses any different source or repeated application and can emit only
a patch to a fresh file. `fix.patch` is the generated repair for that source.
Patched source SHA-256:
`841cb77f63915b19d3afd25efe02a71fbdc06f1df2f1a205170201f1b8411223`;
patch SHA-256:
`b0f03a462912feb8da78d17b703fef3dd8dc5ee280ad4fa2d0eda533d678492b`.
No production tree, existing row, executable or serving process is modified.

Validation:

```bash
python3 -m pytest -q scripts/diagnostics/dtree-prompt-rebase \
  --basetemp=/mnt/raid0/llm/tmp/df2/dtree-prompt-rebase/pytest
```

The original six tests pass. The behavioral test extracts the actual pinned
`spec_tree_resolve` method and the later prompt accept statements directly from
the Git object into temporary C++ translation units. Model-free doubles supply
the surrounding APIs, including predetermined oracle acceptance lengths and a
recorded memory-commit column count. The unmodified source fails; the repaired
source passes 630 combinations (main length 1–7, alternative length 1–9, every
nonempty accepted prefix, winning/losing alternative), compiled with warnings as
errors and UBSan. This checks prefix tokens, next position implied by length,
sampled correction/bonus token, committed column count and winner bookkeeping.
It does not execute real tensor/memory kernels, DFlash, MTP or the full server.

Next, apply this patch in an isolated experimental candidate through the kernel
build row workflow. Require content-bound artifacts and a fresh qualification
that reaches a shorter alternative win and continues to the next tree round,
then rerun the unchanged P5 protocol. Do not resume a previous result directory
across source identities. The A3B row was filed below-baseline futility; see `docs/reports/df2-dtree-p5-a3b-20261120.md`.

## R5 deferred-commit regression (2026-11-20)

The already-published `ak-dtree-build-gpu-20261120-r5` uses experimental
`51b885a8cbd32ee8b0105dea54a18260fb3adbec`. Its deferred memory commit fixes the separate
issue of committing a greedy count before the sampler's accepted count is known.
It does **not** replace the prompt's pending main-draft suffix when the winner
changes. The prompt repair is still required at that source identity.

`port.py` now accepts exactly the two pinned original source digests (47f08e797
and r5), and refuses all other or already-repaired inputs. The r5 source digest
is `32fc3599d0abc0c50930aac2c164c6bbc75c2abaf9631e3c086ea4e41f671575`. Its generated
`r5-fix.patch` SHA-256 is
`1e46a8d7df3e4a20432de843f07543a30ea215db449f4aaa70e64decb82711cd`;
repaired r5 source SHA-256 is
`6c0873569fadcfcf626bb879fed8474a5fe63cb7cf003d81c49deafb1f579c7f`.

Eight model-free tests PASS. The r5 regression extracts its actual resolve,
deferred commit and prompt-accept statements into the C++ doubles and runs
under UBSan with warnings as errors. Unmodified r5 fails on a seven-token main
draft replaced by a one-token alternative with zero sampled drafts accepted:
the prompt still contains six excess tokens while memory commits only the anchor.
The repair passes **2,100** cases across main lengths 1–7, alternative lengths
1–9, winning/losing alternatives, and sampled acceptance 0 through the selected
greedy prefix. It checks prefix/content, pending-column clearance, sampled bonus
and the next-root position implied by prompt length versus committed columns.
The original 47f08e797 regression still passes its **630** cases after repair
and fails without repair.

These are source-level tests with predetermined acceptance and a memory-commit
double. They do not execute a real next decode round, prove runtime tensor
correctness, attribute the observed T12 failure, or establish speed. The queued
r5 build and all queued timing rows are untouched. Apply `r5-fix.patch` to a new
isolated experimental candidate after the kernel owner's current build boundary;
content-prove the resulting build and require a real shorter-winner continuation
qualification before new 27B P5 timing. Do not reuse an older result directory.
