# R7-bound prospective g2-S2-B witness

Row `kvu-kpf174d-witness-r7-20261119` packages the already-filed R7 full build.
The reproducible preparer is `scripts/benchmark/kpf174d_publish_r7.py`.
Runtime scratch root: `/mnt/raid0/llm/tmp/kvu/kpf174d-witness-r7-20261119`.
External receipts, model-identity record, linkage helper and serving artifacts
are referenced in place; no external source tree, log or binary is copied.

Scope is one prospective diagnostic pair on frozen **g2-S2-B**, a 1,984-token
fork and 64 output tokens. The exact input file is preserved. g0-S2-B and
g1-S2-B are permanently excluded; missing/duplicate targets and substitutions
are refused before server start. A `.started` marker consumes the cell.
SMOKE_ONLY requires valid token/logprob shape, two positive own-process VRAM
samples within each request, receipt-bound serving artifacts and mapped DSOs,
matched conservative physical layout, and verified server cleanup. Otherwise
INVALID or INVALID_LAYOUT. Stop on answer, STOP, deadline or the first
custody, layout or residency failure; interim gates remain futility-only.
No near-tie correctness test, five-cell job or historical re-judgment is enabled.

Source `6ec877068936588b6d63dbba5842bbd540b92031`, parent
`84d0a31603d495377dee24e1159bbbf02f1e2f21`; model Qwen3.8-27B Q8_0.
The R7 receipt, custody manifest and linkage-helper pins are checked during
preparation and in the sealed runtime. All eight serving artifacts and all
seven application/ggml mappings retain the current fail-closed custody gate.
Research imports retain `pinned_harness.py`'s four source/argv digests.

Publication uses a separate model-free HIP allocation probe under the keeper's
four-CPU smoke. It writes only an isolated native-attempt receipt, holds the
allocation for the keeper's residency sampler until stopped (120 s maximum),
and cannot expose a target or complete the diagnostic row. The grant runs the
actual pair through `control.py --smoke`; no model content is hashed inside it.
Existing prepared model identity is reused only after exact stat comparison.

Validation: 73 model-free tests PASS, including exposed-cell substitution,
missing/duplicate selection, source import and all serving-library mapping
refusals. Shell syntax PASS. GitNexus status/impact are unavailable because this
lane has no index; edits affect only this prospective runner and its preparer,
with no production kernel, daemon or coordinator edits.

The first publish attempt was refused before smoke because SOURCES.sha256
included the mutable shared rowflow engine. The corrected seal excludes that
engine; the keeper records engine identity in PASS.json. All task-owned runtime
files and external receipt/helper content remain sealed. The preparer recreates
one packet root; no model or target was exposed by the refused attempt.

Prepared file pins (SHA-256; evidence retained in place):

- `/mnt/raid0/llm/tmp/kvu/kpf174d-witness-r7-20261119/spec.json`: `40fb4407daa668f0878fbd5f7292c32ba0f0843e347de224f12783762cc98d1e`.
- `/mnt/raid0/llm/tmp/kvu/kpf174d-witness-r7-20261119/prospective/SOURCES.sha256`: `86ecca543f57176b80720e966fd46274c2e6a1a0ec900dc326b7c58a271ce0a0`.
- `/mnt/raid0/llm/tmp/kvu/kpf174d-witness-r7-20261119/prospective/BUILD-PROOF.json`: `74ffd718a9e50b614b305d4e6fec09aea8c13c46f72d14ae04659ad5f0b2edd6`.
- `/mnt/raid0/llm/tmp/kvu/kpf174d-witness-r7-20261119/prospective/PREDECLARED.md`: `af88632915381174ae42ef5f8bc03b5f42f52141e4a0e911f9550ffc84472f3f`.

## Publication outcome

Corrected publication accepted on 2026-11-19. `publish_row.py --smoke-now`
reported **GPU busy: smoke queued**; it did not run or report PASS. The keeper
will run the isolated admission probe in the next GPU gap. Publication does not
establish readiness, native qualification or a diagnostic result. Consume its
smoke event before calling the row ready; consume the later grant result before
filing any layout verdict. Historical verdicts and the parent box stay open.
[no-belief: model-free software validation and publication checkpoint]
