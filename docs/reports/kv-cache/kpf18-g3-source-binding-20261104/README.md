KPF-18 item 3 group-3 model-free qualification result

Concrete blocker: the private candidate's SOURCES.sha256 pins fork-launch-native.raw (expected SHA-256 192c06830316e13c0b86df1c3167aa653667f161ff966ec2d80694d26eb93689), but the file was absent from candidate/. This made the full candidate source-manifest check fail and prevented its exact fork-binding regression test from loading the captured fixture. The candidate's test_fork_binding.py expects that file; no model/GPU/runtime action is needed to diagnose this.

Repair proof: I left the private candidate untouched. In isolated workspace /mnt/raid0/llm/tmp/heterogeneous-slot-fabric-residency/g3-qualification/candidate, I copied the candidate tree and restored the pinned fixture from the canonical retained source /mnt/raid0/llm/tmp/codex-ni-20261027-kpf18-normalization-r13/source/fork-launch-native.raw. The retained source and replay-prep copy both hash to the pinned digest. This is an exact restoration, not reconstructed/generated evidence.

Validation:
- In the unmodified private candidate, `sha256sum -c SOURCES.sha256` failed only on missing fork-launch-native.raw; every other entry passed.
- In the isolated repaired copy, `sha256sum -c SOURCES.sha256` passed all entries.
- In that copy, `python3 -B -I test_fork_binding.py` passed 5/5 tests, including exact captured fork/task/launch binding and ambiguity/conflict refusal cases.
- The workspace copy is at `/mnt/raid0/llm/tmp/heterogeneous-slot-fabric-residency/g3-qualification/candidate/`; restored fixture SHA-256 is `192c06830316e13c0b86df1c3167aa653667f161ff966ec2d80694d26eb93689`.

Scope: model-free fixture/source-custody qualification only. No handoff/index edits, grant operations, build, model, GPU, benchmark, publication, or candidate entry-point execution. The original candidate still requires its owner to restore this exact retained file before its own manifest/test gates can pass; no READY claim follows.
