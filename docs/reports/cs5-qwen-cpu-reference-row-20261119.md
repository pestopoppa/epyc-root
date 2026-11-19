# CS-5 Qwen CPU reference row — 2026-11-19

Published `stt5-cs5-qwen-cpu-reference-r1-20261119` through `publish_row.py`.
The publisher returned **queued for keeper smoke**, not PASS. No model execution,
CS-3 output, accuracy, TTFA, GPU residency or completed CS-5 is claimed.
The smoke must finish a real native audio turn and emit its CS-3 sidecar before
this row becomes ready. Do not poll; consume the dispatcher event.

The engineering question is whether the native Qwen arm can execute one local
public JFK turn through the existing reference job and CS-3 writer. Each attempt
stops after that turn, a terminal failure, or the grant deadline. Generation is
bounded by thinker 32 and talker 64 new tokens, with sampling disabled. The row
requests a CPU quarter and 1,800 seconds. Non-streaming completion latency has
lower-better direction; one turn supports no accuracy or latency comparison.

The once-only preparation ran outside a grant. Its 84 receipts cover
70,530,983,248 bytes: the complete local model-directory inventory, public input,
sampler and executed reference scripts. Each receipt binds SHA-256 and before/after
stat identity. Both actual configurations passed `admit` and Qwen `verify_sources`
without model loading. Runtime admission checks the prepared stat identities,
three core package versions and the existing three direct source pins; it is not
a full transitive code/environment seal. All 67 installed package versions are
recorded for diagnosis. A real import check passed for both Qwen model/processor
classes and `qwen_omni_utils.process_mm_info` after adding the missing torchvision
and torchaudio dependencies.

The dedicated runtime is `/mnt/raid0/llm/tmp/stt5/cs5-qwen-env-20261119`:
Python 3.12.15, torch 2.6.0+cpu, transformers 5.5.1,
qwen-omni-utils 0.0.8, torchvision 0.21.0+cpu, torchaudio 2.6.0+cpu,
accelerate 1.13.0, soundfile 0.13.1 and librosa 0.11.0. Offline and CPU visibility
flags are explicit; thread counts come from the grant. This runtime does not
satisfy the separate gfx90a requirement.

Source/input identities:

- Root code: commit `4e2650557738ae575d0ed9ca98e30fb123fe20b8`,
  `scripts/speech/cs5_reference_job.py`, `cs5_qwen_reference.py`,
  `cs5_step_reference.py`, and `cs5_step_adapter.py`; retained in a locked sparse
  detached worktree at `/mnt/raid0/llm/tmp/stt5/cs5-root-source-20261119`.
- Qwen native checkout: `models/speech-d1-20261020/src/Qwen3-Omni` under
  `/mnt/raid0/llm`, commit `e4235853125589c789f06a2dd83e9f4126df5e9d`.
- Local Qwen model revision: `26291f793822fb6be9555850f06dfe95f2d7e695`;
  the complete local file identities are in the configurations below.
- Public input: `/mnt/raid0/llm/whisper.cpp/samples/jfk.wav`, receipt in each config.

The sampler observes only the CPU frontdoor at port 9467; it makes no host-wide
idle assertion. It requires exactly one matching live process with explicit GPU
layers zero, reads live `/slots`, and checks PID start ticks around that request.
It records model, CPU placement basis, actual slot count and processing booleans,
PID/start ticks, boot ID and sample time. Missing/ambiguous process, unavailable
endpoint or malformed slot state fails rather than inventing an idle state.
Preparation observed that frontdoor processing its one slot; the row must sample
again inside the native turn. This is a bounded instantaneous sample, not an
observation covering the full turn.

Existing-file SHA-256 identities, all under
`/mnt/raid0/llm/tmp/stt5/cs5-qwen-qualification-20261119/`:

| File | SHA-256 |
|---|---|
| smoke-config.json | `af0293519cef2bf64b0807132e014865e3e0e4eefd9710170c0049f6135dfa83` |
| run-config.json | `4e658e3589046dde5b241b58bae1821fe9c091b0f2d2deb558edd938c6db364e` |
| environment.json | `e088baf181c7fd5884419fd87603fed1b4e5e9174505c47eb8d464e4ac4d7dfd` |
| sample_frontdoor.py | `c5d515094f6ed580642bd6b14e62ca5d51a3816e46ce19d2231210aa4df8de48` |
| prepare.py | `b4e0c117462310f39e77096475b17234b9ada970af95aeec72c7156091f9a53c` |
| job.sh | `965dfa3e746981dcd07124d851a92cb700c422c10bc1e9faf053d427fe508ff6` |
| launch.sh | `63e0c890b4ac97dcc0865e815ee2429d1bb1956a28c5c7e76ac33ddda4ed1bfa` |
| spec.json | `8e3baf0b77cfb3ae5392ea6cfc65e2c32e0a85dfd272fe0b47588a9c30d6597d` |
| smoke_check.py | `9e70e24281750f592c3ff4ca8011a348e93695e7a9241d9b3bd1b13813661d58` |

Terminal results belong at `run-output/summary.json`; smoke uses
`smoke-output/summary.json`. PASS requires the job's pass verdict and actual CS-3
sidecar. Native audio failure is FAIL. Admission/load failures, interruption,
missing terminal output or missing sampler witness are INCONCLUSIVE/UNKNOWN,
never successful qualification. Existing native CS-3 write-side enrollment is
unchanged; this preparation creates no measurement claim.

The handoff's question and explicit stop-on-answer/futility wording were added
for publisher admission. GitNexus status/impact were unavailable because this lane
is unindexed; the tracked change is additive task scope and this report, with no
application callers changed. Shell syntax and all 29 existing model-free CS-5
tests pass; those tests do not qualify the newly prepared real row. Step runtime
preparation, actual smoke, both native arms, research-repo packaging and ROCm
qualification remain open.
