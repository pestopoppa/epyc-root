# CS-5 Step audio-generation adapter — 2026-11-19

Implemented `scripts/speech/cs5_step_adapter.py` as the reusable Step reference
compatibility seam. Eight model-free regression tests pass. This is an
engineering code result, not a completed CS-5 reference harness or a GPU result.
The code is staged in the root lane; integration into the research harness is
still required, alongside Qwen, Token2Wav device handling and CS-3 records.

The retained model source drops `wavs` and `wav_lens` whenever a non-null
`past_key_values` is supplied. Its content SHA-256 is
`82b93db45a4bf37c2877660b321782aea4715e3e0d7be221e91e99e13815cbe3`, at
`/mnt/raid0/llm/models/speech-d1-20261020/Step-Audio-2-mini/modeling_step_audio_2.py`
(lines 376–398). The previous successful D1 probe's implementation is retained at
`/mnt/raid0/llm/tmp/overnight-gpu-arm-20261022/d1_probe.py`, SHA-256
`77732ffd49c6fe38c6316c15fac9bdffe090a1b1679ae127a48f908f828851a6`.
Upstream StepAudio2 source is commit
`76e272b56c3917a8d7188f18bbb5a65dfc8a0845` in
`/mnt/raid0/llm/models/speech-d1-20261020/src/Step-Audio2`.
No source trees or original logs were copied into evidence directories.

The adapter keeps full input IDs and audio on every generation step and
requires `use_cache=False`. It calls the upstream StepAudio2 instance directly,
retaining its native StepFun message formatter. Explicit `wavs`, `wav_lens` and
`**kwargs` names preserve the generation argument validation contract. A scoped
encoder pre-hook records calls; zero calls on an audio request report
`audio_path_never_ran` with raw output preserved. Per-instance overrides and
hooks are restored even when generation throws. Callers must serialize access
to each model instance.

A single leading Chinese language tag is removed from the separate cleaned
text field; raw text, native tokens and audio are retained. Interior tags and
special control tokens are untouched. No coherence grade is inferred from
encoder activity, and no model execution, placement, latency, CS-3 record
certification, timing or production change is claimed.

Validation: `python3 -m unittest discover -s tests/speech -p test_cs5_step_adapter.py`
passes all eight tests. Controls cover non-null caches at successive steps,
audio bypass, text-only requests, generation failure cleanup, pre-existing
instance overrides, class isolation, forced cache refusal and prefix-only
cleanup. `git diff --check` passes. GitNexus status and impact are unavailable
because this lane is unindexed; this new module has no existing callers.

CS-5 remains open. The existing conversation-stack source enrollment applies;
this model-free compatibility seam emits no measurements or graded findings.
No new claim ladder or retrospective measurement warrant was created.
