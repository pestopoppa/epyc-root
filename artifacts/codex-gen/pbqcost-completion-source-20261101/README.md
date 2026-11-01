# PB-QCOST completion source candidate

The filed confirm-q result remains a completed negative diagnostic. This is a
source-only candidate to correct the completion checker for future use; it is
not installed, published, or a request to repeat the measurement.

The complete sealed candidate, including the unchanged captured-input fixture,
is at `/mnt/raid0/llm/tmp/codex-gen-pbqcost-completion-source-20261101/`.
This directory archives changed source and tests only, so its source manifest
is an identity reference and is not expected to verify against this subset.
The local complete packet's source seal and 12 focused tests passed. Recovery
re-derives the verdict from six pinned inputs and rejects changes to each; the
sealed producer refuses a sibling-directory override. `COMPLETION-BINDING.md`
is preserved byte-for-byte from the sealed packet; its raw-input shorthand
does not enumerate those additional pinned inputs.
