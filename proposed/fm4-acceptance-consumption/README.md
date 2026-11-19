# FM-4 prospective acceptance consumption review

D9 operator acknowledgment is pending for the proposed oracle change. The patch covers `scripts/coordination/session_oracle.py` and `tests/coordination/test_session_oracle.py`.

- Prepared against commit `2309a330f83d5f7ae3f4370c9715c9125a967e56`.
- Oracle base blob `a74b7ca09ab642c9fc64597fc015d853519e2a3a`.
- Oracle tests base blob `83f5edc37496f69190535fe4f7520eefc29a06a6`.
- Existing producer blob `33673af415757025255628a3c7a8b332d15c9a97` at `scripts/experiments/fm4/task_acceptance.py`.
- Patch SHA-256 `34191d1de08fe886e72521fbcc6e47dc249b6a33ebf09664248df195f29ca69f`.

Run the check from the repository root. Apply only after D9 acknowledgment.

```bash
git apply --check proposed/fm4-acceptance-consumption/acceptance-consumption-d9.patch
git apply proposed/fm4-acceptance-consumption/acceptance-consumption-d9.patch
python3 -B -m pytest -q tests/coordination/test_session_oracle.py tests/coordination/test_replay_session_oracle.py tests/experiments/test_fm4_task_acceptance.py
```

The focused suite passed 128 tests. The standalone script also passed `python3 -I -B scripts/coordination/session_oracle.py --help`. GitNexus status and upstream impact were unavailable because the lane had no index. Static caller review found the standalone CLI and the frozen replay caller in `scripts/coordination/replay_session_oracle.py`. Existing callers use the default without acceptance inputs.

```bash
python3 -B scripts/coordination/session_oracle.py \
  --files /private/fm4/agent-child.jsonl \
  --parent /private/fm4/parent.jsonl \
  --task-id FM4-example \
  --task-acceptance /private/fm4/task-acceptance.json
```

The CLI accepts one child and repeatable record paths. The Python API accepts `assess(child_path, parent_path=parent_path, task_id=task_id, acceptance_paths=paths)`. The caller obtains the task ID independently from the dispatch context. Native transcripts lack a structured task ID, so the caller supplies that binding. The child and parent transcripts establish the other three identities through a terminal structured Agent or Task result. A single parent dispatch must identify exactly one child.

The producer validator rechecks the versioned shape and retained evidence on each opted-in assessment that reaches record verification. Every supplied file must match and validate. Identical parsed records can repeat. Distinct matching records, an unreadable or malformed input, an identity mismatch, or mutated evidence preserve the baseline verdict. Local success, failure and partial verdicts and explicit parent outcomes retain precedence. The oracle emits `signals.task_acceptance` with the disposition, caller task ID, expected identities when available, source paths, record-byte hashes when readable, and verified record metadata. A declined join is visible in the row while the CLI retains its normal classifier exit behavior.

The proposal targets the current parent join. A launch-only or running parent result declines acceptance. The separate notification proposal represents a terminal notification on an initially asynchronous result with a new field. Recognizing that field requires integration work and fresh validation when both changes are considered. The patches share oracle context and may require a rebase. This package covers focused controls with generated records and transcripts. Authorship of the gate decision and suitability of the gate remain assumptions of the producer's caller.
