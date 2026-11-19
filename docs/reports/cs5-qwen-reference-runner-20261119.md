# CS-5 Qwen native reference runner — 2026-11-19

The root-lane Qwen runner now uses the native Qwen3-Omni chat template,
multimodal processor, thinker generation and talker audio interface. Both
candidates share the existing CS-3 native-attestation writer. This is a tested
integration seam, not completed CS-5 or a qualified model run.

Source identities (root git blobs):

- `scripts/speech/cs5_qwen_reference.py`: `708cd2f8c232a29eee87bf8901762ba9de9bd5e9`
- `scripts/speech/cs5_step_reference.py`: `80c905e50637ba213cde3df88dfe1ea04ebaf054`
- `tests/speech/test_cs5_qwen_reference.py`: `6e8598d6c616ce4ad74c2229d7029dc69ee69ad2`

The retained upstream checkout is
`/mnt/raid0/llm/models/speech-d1-20261020/src/Qwen3-Omni` at
`e4235853125589c789f06a2dd83e9f4126df5e9d`. Its native README snippet
(lines 260–321) supplies the processor/generation sequence; README SHA-256 is
`013dbbd14768e7767a05d6a5da8dffecd0b8f36938eedaa6a5000c26484f4603`.
No original files were copied. No web documentation or current upstream behavior
is asserted beyond that retained source.

`load_models(source_dir, model_dir, device, environment=...)` refuses changed
upstream state and requires caller-frozen installed versions for torch,
transformers and qwen-omni-utils, plus distribution-relative source hashes for
the Qwen modeling/processing implementation and omni utility entry point. These
pins must be prepared before publishing; they are not a complete transitive
environment seal or weight identity. Loading is local-only with explicit device,
SDPA attention and model eval mode. Actual installed API compatibility and ROCm
execution remain untested. Source checks never hash model weights.

`run_turn` requires local audio files and a live co-tenant sampler, uses the native
prompt and processor, and refuses absent audio features when audio is expected.
It forces text-plus-audio output and preserves generated thinker tokens,
raw/special-token text, cleaned text, source/environment identities and WAV digest.
Missing generated audio writes a native failure without a success latency record;
empty/nonfinite audio raises. Presence of processor features is an input witness,
not an encoder-execution witness. The future qualification must prove encoder
execution and actual device residency during the run.

Timing synchronizes before prompt/processing/generation and after generation;
it includes co-tenant sampling and excludes decoding and WAV serialization.
It is completion time, not TTFA, and differs from Step's scope including
Token2Wav conversion; comparisons must retain those scope labels. Generated
Qwen audio is serialized as the native documented 24 kHz waveform. Generic
CS-3 output preserves candidate-specific source/producer fields, reference
runtime, lower_better latency, reps=1 and null protocol. No serving or admissible
protocol claim is made. Existing VB-SPEECH-CONV-1 source/writer registration
covers these records; no new ladder or successful planning-context canary.

Validation: `python3 -m unittest discover -s tests/speech -p 'test_cs5_*.py'`
passes 22 model-free tests. Qwen controls cover native output and timing,
missing input features, missing output audio, forced generation contract,
network/modality refusal, upstream/version/source drift and CS-3 tamper refusal.
Existing Step controls also pass. `git diff --check` passes. GitNexus status
and impact cannot run because the lane is unindexed; the new runner has no
existing callers, and the shared writer change is covered by both candidates.
No model execution, publisher smoke, GPU/ROCm, WER, TTFA or promotion result.

Next: freeze prepared corpus/weights receipts and complete environment identities,
package the two root APIs for research execution without copying upstream trees,
and publish CS-5/CS-8 qualification using publish_row.py. CS-5 remains open.
