# CS-5 Step reference runner integration — 2026-11-19

`scripts/speech/cs5_step_reference.py` integrates the existing compatibility
adapter with pinned native StepAudio2 and Token2Wav loaders, explicit device
placement, synchronized non-streaming completion timing, and the existing CS-3
conversation-stack writer. Fifteen model-free tests pass across adapter and
runner. This root-lane API is ready for research-harness packaging; it is not a
completed two-candidate CS-5 harness or a qualified ROCm run.

Upstream checkout: `/mnt/raid0/llm/models/speech-d1-20261020/src/Step-Audio2`,
commit `76e272b56c3917a8d7188f18bbb5a65dfc8a0845`. The loader refuses a changed
commit or tracked dirty state, and verifies both source files before executing:

| File | SHA-256 |
|---|---|
| `stepaudio2.py` | `9bd85c95a38b2273388ed4cc024d4a5aca9f585b8c51f04c25515078313a81b4` |
| `token2wav.py` | `37a13e82d7a0cc656d465197f3c7ac61b8029ae85c91e7ca606cb4c6010974c7` |

The retained model-side `modeling_step_audio_2.py` must match SHA-256
`82b93db45a4bf37c2877660b321782aea4715e3e0d7be221e91e99e13815cbe3`
before construction. These are source identities, not a weights identity or a
claim that a loaded runtime executed. No original files were copied.

The loader executes a narrow AST placement overlay in private module namespaces.
Every zero-argument `.cuda()` becomes `.to(explicit_device)`; CUDA device keyword
allocations use that device, and autocast receives its device type. This covers
both Step's input/model allocations and Token2Wav's flow, vocoder, prompt and
stream-cache allocations. Unexpected `.cuda()` signatures fail closed. Native
StepFun prompt formatting and generation remain upstream code. Global torch
methods and upstream files are untouched. Use a dedicated row process because
upstream absolute imports remain process-local; dependency versions and prepared
weights/input identities still need freezing in the research launcher.

The API sequence is `load_models(source_dir, model_dir, device)`, then
`run_turn(model, vocoder, messages, ...)`, then `write_turn(out_dir, result,
run_id=..., subject=...)`. Loading returns a device-specific synchronization
callback. The caller supplies the prepared prompt WAV, generation settings,
whether input audio is expected, harness model/quant/device/host-lane metadata,
and a live co-tenant sampler. No default idle tenant is invented. Runtime kind is
forced to `reference`; its identity includes upstream commit and both runner and
adapter code hashes. Calls to one model instance must be serialized.

Each turn retains messages, prompt path, raw/cleaned text, native tokens and
audio tokens, encoder witness, cache-disabled settings and source pins.
Successful turns save WAV bytes with their digest and a native JSON attestation.
The shared `conversation_stack_measurement.write_belief_measurements` writes
`turn_latency_ms`, `lower_better`, `reps=1`, `protocol_id=null`, reference runtime
and observed co-tenant metadata. Timing spans prompt processing, generation and
Token2Wav with synchronization at both edges; it includes sampler overhead and
excludes model loading and output writes. It is not TTFA or a streaming measure.
An audio-path bypass or empty generated audio produces native failure evidence
without a success latency sidecar. Exceptions propagate to the future row's
failure handler. Existing output directories refuse replacement.

Validation: `python3 -m unittest discover -s tests/speech -p 'test_cs5_step*.py'`
passes **15 tests**. Controls exercise explicit placement without torch-global
patching, changed-source refusal, unexpected CUDA signatures, audio bypass,
unknown co-tenant rejection, output reuse refusal, and native output through the
existing writer/projector. Editing an attested native file clears its projected
attestation presence. Both actual pinned upstream sources compile through the
overlay and contain zero remaining `.cuda()` calls after transformation.
`git diff --check` passes. No models were imported or executed for these checks.

GitNexus status and upstream impact are unavailable: this lane is unindexed.
The new module has no pre-existing callers; production launchers are untouched.
The existing VB-SPEECH-CONV-1 source/writer enrollment covers these prospective
records. No new source ladder, grading rule, retrospective warrant or successful
planning-context canary is claimed. Qwen integration, research-repo packaging,
prospective input/weights/environment pins and a published CS-8 qualification
row remain. CS-5 stays open.
