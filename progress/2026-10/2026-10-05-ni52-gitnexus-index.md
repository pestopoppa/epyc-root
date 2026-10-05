# NI52 — Off-host GitNexus snapshot refresh (2026-10-05)

NI52 refreshed GitNexus on a bounded immutable GitHub runner because the canonical
index was stale relative to the reviewed source. The indexed source is commit
`c8851695cc6ae46845c06b9f60402e687f1698ec`; it is a historical snapshot, not a
claim about the current `origin/main`. The workflow and source commit chain are
captured in the install artifact, and both recipe commits changed only the workflow.

The first attempt, run `37356899671`, remains preserved as a failed recipe attempt.
GitNexus completed its index, but a nested metadata heredoc broke the wrapper before
impact validation finished, and the `OpenAIChatRequest` name query was ambiguous.
Those raw originals were preserved separately at
`/mnt/raid0/llm/artifacts/ci/ni52-gitnexus-index-37356899671-original-download/`;
they were not replaced or relabeled.

The corrected, push-triggered run `37358369281` completed successfully in 1m49s on
recipe commit `d714f40f9c235501f5b15f425ef348598470a909`. Its four downloaded workflow
prefixes are preserved at
`/mnt/raid0/llm/artifacts/ci/ni52-gitnexus-index-37358369281-original-download/`;
the 79-file downloaded-byte manifest is
`/mnt/raid0/llm/artifacts/ci/ni52-gitnexus-index-37358369281-download-sha256sums.txt`
(SHA-256 `071c92cdadfeed0e5bb803d34a54937c255ce2eda58fedc260d7139da4be70d6`). Every
recorded tool, analyzer, status, impact, impact-validator, and metadata status was
zero. The exact upstream targets were
`Function:scripts/autopilot/strategy_projection_report.py:build_strategy_projection_report`
and `Class:src/api/models/openai.py:OpenAIChatRequest`; each validator confirmed
`epistemic=exact`, with `risk=LOW` for both. Metadata records 3,376 files, 75,241
nodes, 138,642 edges, 2,922 communities, 300 processes, and zero embeddings.

The runner used the SRI-verified GitNexus 1.6.8 tarball and the accepted 270-entry
lock (`734c187820f8e972354dec7aa7519ce37bf0b688530ef83623d8baeb645b448c`) with
Node 22.14.0 and npm 10.9.2. `npm ci` had lifecycle scripts disabled; the captured
native proof records no compilation, telemetry postinstall, or ONNX postinstall.
The source postcheck permits only the generated ignored index, and the independent
bus postcheck confirms the bus path was absent and not a symlink. No index bundle was
uploaded because the accepted outputs were bounded metadata, status, and impact
records; the index is reproducible from the pinned source and dependencies.

Main independently read back all 79 downloaded files and their manifest, source and
recipe ancestry, package/tool/native attestations, every command and validator
status, exact targets and LOW risks, source cleanliness, and bus/index postchecks,
then accepted the result as ordinary offline code-intelligence dependency evidence.
This creates no `ClaimTuple`, adds no scientific source class, and does not register
or replace the canonical host index. No host index build, runtime observation, or
production change was performed.
