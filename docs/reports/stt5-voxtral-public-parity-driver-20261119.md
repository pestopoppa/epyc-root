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

## Public-parity row preparation and argv correction

The original weight-restoration receipt now reports PASS: pinned revision,
4,733,486,848 bytes and original Q8 digest match. Its recorded device/inode/size/mtime
identity passes the driver preflight. No second model hash was performed.

Before publication, source inspection found the driver used the independent
transcribe CLI backend convention. CrispASR instead selects the model with
`--backend voxtral4b`; CPU is `--gpu-backend cpu`. Corrected the driver and
argv regression to use both, `--no-gpu`, one thread and the original reference
recipe (`--no-timestamps -l en`). All 20 model-free Voxtral tests pass.
GitNexus status/impact report no index; the edit is confined to this standalone
driver and its test.

Prepared public-JFK configuration binds both final rebuilt runners, three ggml
libraries and the delay-specific Crisp library, original audio/references,
restoration receipt and build summary. Distinct smoke/grant output directories
retain native witnesses, exposure receipts and sampled mappings. Existing ten
validation results and eleven exposures, including UNKNOWN, are unchanged.

Inputs are referenced in place; no model, binary, log or source-tree copies
were added to the repository. Prepared identities:

- `/mnt/raid0/llm/tmp/stt5/voxtral-parity-20261119/config.json` SHA-256 `92a48ca4f7e920503f41c71e5a8a799d8bf4e31441094dae39e527ba1d2a0420`.
- `/mnt/raid0/llm/tmp/stt5/voxtral-parity-20261119/spec.json` SHA-256 `4a208a86571a1095a0510b0c7446f78f05eed9a514a20ca0668d83cdab7f038c`.
- `/mnt/raid0/llm/tmp/stt5/voxtral-parity-20261119/launch.sh` SHA-256 `a89afc1bb96941876df79b4593d0d43a7ae3a8b9ce8c896b75b933b7d095ef41`.
- `/mnt/raid0/llm/tmp/stt5/voxtral-parity-20261119/stt5_voxtral_parity.py` SHA-256 `ce6a2148e744bcbce197063228cfb417cc8629f8c4dfb2b18923362d7ada7f10`.
- `/mnt/raid0/llm/tmp/stt5/voxtral-parity-20261119/stt5_voxtral_tokens.py` SHA-256 `28382a292d5d060bbd4c27d561973a55a60ef58d1d763bb8f607fc3726677063`.
- `/mnt/raid0/llm/tmp/stt5/voxtral-parity-20261119/smoke_check.py` SHA-256 `71369f570e4c9290cd295f77fd2ce69c72ae21cd694f13d029bccc9e3e37d8ca`.
- `/mnt/raid0/llm/tmp/stt5/voxtral-weights-20261119/restore-result.json` SHA-256 `06dbc8cacefbbab4d57ec17bd834228ce7bceab338aede3484a1ff1f9ab365e2`.

Publication invoked through `publish_row.py .../spec.json --smoke-now` for
`stt5-voxtral-public-parity-r1-20261119`. The synchronous publisher remains active at checkpoint;
no smoke PASS, grant parity or validation claim is made. PASS and FAIL-1 terminal
files are registered for dispatcher resumption. The result-bearing code change
corrects backend selection before any inference successor can be admitted.
