# Voxtral public-JFK parity driver — 2026-11-19

CS-8.STT5: implemented `scripts/speech/stt5_voxtral_parity.py`.
All 20 Voxtral model-free tests pass (eight new parity-driver tests plus
four comparator and eight rebuild tests). No model execution or validation
exposure occurred. This is tested engineering code; no row was published,
no publisher smoke or public-fixture parity is claimed, and the parent stays open.

The driver runs exactly the 480/960 ms pair on public JFK with one CPU thread,
GPU visibility disabled and the native CPU/no-GPU flags. It requires the original
JFK digest and delay-specific reference-log digests, a non-smoke PASS build
summary at CrispASR `2aa8d7669fcaa18d98d61a4bc8a077464e6b9919`, and every selected
runner/library digest bound to that build's final artifacts. Source/runtime,
reference, config and model-stat drift refuse. Original Q8 weights require the
PASS restoration receipt, original revision, digest, size, path and prepared
stat identity. The driver never hashes model bytes; model pins, symlinks and
hard-link aliases are refused before hashing.

Each delay exclusively reserves its output directory before its exposure
receipt or process launch. Existing directories refuse even if the prior
receipt is missing, so interrupted/unknown exposures cannot be redrawn.
The driver drains only its captured child, escalating TERM to KILL and reaping
before proceeding. Native stdout/stderr hashes and sampled mappings are retained.
Missing/foreign ggml or Crisp libraries, nonzero exit, interruption or malformed
native witnesses cannot pass. Complete native ID disagreement reports FAIL;
exact agreement reports PASS only with the residency contract satisfied.
The summary establishes public-token parity only outside smoke. It makes no
transcript, WER, accuracy, rate or promotion claim.

## Preparing the row

Configuration fields: `model`, `model_receipt`, `build_summary`, `audio`,
`pins` (absolute small-file path to SHA-256), `output`, `smoke_output`, and
`variants` with exactly `480` and `960`. Each variant requires `runner`,
`reference`, `expected_maps` (resolved library paths) and `library_path`.
Pin the restoration receipt, build summary, public audio, both original
references, both final runners and every expected library. Bind launcher,
driver and comparator identities at publication. Use distinct fresh smoke
and grant outputs. Publish through `publish_row.py`; its real four-CPU smoke
remains mandatory. No model hashing or preparation belongs inside the grant.

At this turn's prerequisite check, the registered restoration receipt
`/mnt/raid0/llm/tmp/stt5/voxtral-weights-20261119/restore-result.json`
was absent and only the partial download existed. No wait or retry was run.
Next: consume that receipt when available, prepare the final-runtime-bound
configuration, then publish the two-delay parity row. Preserve all original
ten validation results and eleven exposures, including the exposed UNKNOWN.

## Validation and identity

`python3 -m unittest discover -s tests -p 'test_stt5_voxtral_*.py'`: 20 PASS.
Controls cover categorical failures/interruptions, missing/foreign mappings,
malformed/duplicate witnesses, unequal full-ID lists, exclusive exposure and
receipt writes, CPU argv, owned-child kill escalation, required input pins,
original reference/fixture bindings, receipt digest/revision/path/status,
model-stat drift, runtime rebinding and weight-hash aliases.
`git diff --check` passes. GitNexus status/impact report no index in this lane;
standalone new module, no existing caller or refactor.

Existing conversation-stack enrollment and committed-conclusion observations
apply; no retrospective measurement warrant or new grading ladder.

- `scripts/speech/stt5_voxtral_parity.py` git blob `d808c875e8b0ce3a070d9766de2eb28d5243108b`.
- `tests/test_stt5_voxtral_parity.py` git blob `79a1b23a6c105799dbf0735289dffc3c0889f8d9`.
