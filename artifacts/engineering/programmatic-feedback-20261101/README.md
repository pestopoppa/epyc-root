# Programmatic feedback and TU-ADV source proof

Date: 2026-11-01 UTC

## Published source

The orchestrator implementation is published on `origin/main` at merge commit `f6dff34eb244b3cf3ad99f027b40a583f2393da1`. Its independently tested candidate was `ac48a632af48e6cfc0ac52e08afb585aad16c596`. Implementation commits are feedback `1b988feb006497425417d641a3ecf7816c2f58ae` and TU-ADV source `f6b648dd5167465df82cd327437502e6aeacbacc`; the joint workflow/candidate commit is not the implementation identity.

Feedback extraction records only exact standalone no-op output and repeated canonical actions. Repetition remains intent-unknown, not a failure diagnosis. Closed-shape bounded facts retain event IDs and action/output-text-projection digests, are consumed once as untrusted data by the actual next-turn graph prompt, and leave explanation/planning to the existing LLM path. Raw tool arguments/output are not duplicated. The recorder is constructed by existing logging **or** replay opt-in; logging-off by itself does not imply it is absent.

TU-ADV source adds native provenance checks at the real `DistillationPipeline`/temporary `SkillBank` boundary. Explicit malformed, unknown, failed, mismatched or unverifiable provenance is rejected; absent provenance retains legacy UNKNOWN behavior. This is not completion of the exact external Continual/Pokee cases or global cross-run skill-persistence task. The parent handoff remains open.

## Accepted hosted correctness evidence

- Run: https://github.com/pestopoppa/epyc-orchestrator/actions/runs/41280199807
- Job: `focused-contracts`, job ID `12477 0396671` (concatenate the two digit groups for the API identifier), success; started `2026-11-01T06:17:08Z`, completed `06:18:27Z`.
- Exact tested source: `ac48a632af48e6cfc0ac52e08afb585aad16c596` on `codex/ni-programmatic-feedback-tuadv-ci-20261101`.
- Result: `214 passed, 1 warning in 7.92s`, exit code 0. The warning is the existing PydanticGraph deprecation.
- Command: `python -m pytest -p pytest_asyncio.plugin -q --junitxml="$RESULT_DIR/junit.xml" tests/unit/test_step_events.py tests/integration/test_execute_turn.py tests/unit/test_distillation.py scripts/autopilot/evals/dtap/tests/`.
- Environment: hosted Ubuntu, Python 3.13.15; dependency closure installed with `python -m pip install -e '.[dev]'`. The full deterministic DTAP directory, focused feedback unit/integration tests and distillation controls ran with synthetic fixtures only. No model, live endpoint, production kernel store, or kernel build was used. Config-only kernel path overrides point at nonexistent `/tmp` locations; test artifacts use `/tmp/ni-code-contracts-tmp`.
- GitHub artifact: ID `13072594430`, name `ni-code-contracts-41280199807-1`, 17,700 bytes, artifact digest `sha256:ef31ef336f411a377b5f00d9d73057c3ae170f1f3e9096a93a8201f629f8c72f`, created `2026-11-01T06:18:24Z`, expires `2027-01-30T06:17:05Z`. Complete downloaded artifact is preserved in `hosted-run-41280199807/`; original run/job and GitHub artifact API JSON are preserved byte-for-byte in `hosted-run-41280199807-api-originals.zip`.
- The 17-entry `source-files.sha256` manifest was verified against the candidate and again after source promotion. It includes exact feedback, TU-ADV, test, dependency-lock and workflow inputs. `source-commit.txt` binds the run to `ac48a632...`.

The artifact file hashes are recorded here to preserve custody:

| File | SHA-256 |
|---|---|
| `hosted-run-41280199807/dependencies.stdout.txt` | `310c638b8f48c99a64b4d3084a4ce4573db179105cb3a6799483c8bb4f162aef` |
| `hosted-run-41280199807/pytest.stdout.txt` | `9dc1c4b83a4bdcabfe55f2199c4fa136907a6e9c19577cd1e930a30579c7c8a1` |
| `hosted-run-41280199807/junit.xml` | `112841f4ccd3d00c7c4880c12b8b3e84426ec56735e05ae69f4b2235501d1671` |
| `hosted-run-41280199807/pytest.exit-code` | `9a271f2a916b0b6ee6cecb2426f0b3206ef074578be55d9bc94f6f3fe3ab86aa` |
| `hosted-run-41280199807/pip-freeze.txt` | `4f412bd64ab837338db6833afc74b5c42e7c6470b5935dc83f51e186f370a87b` |
| `hosted-run-41280199807/source-files.sha256` | `3c5aa884533c89cbb35dd37c5e34dd1b99faae3db92c814ecc41bb4aff4eb295` |
| `hosted-run-41280199807/source-commit.txt` | `6fec55e50545e13a17ccf645a9e4c61dc8789e6859788af1a889e4103dd21301` |

## Failed hosted setup attempts, retained originals

Five earlier task-specific CI runs and their downloaded artifacts are preserved byte-for-byte inside `retained-failed-and-excluded-originals.zip` under their original `attempt-hosted-<run-id>/` paths. These are setup failures, not source failures and not accepted validation: run `41279436868` exposed the default kernel-store path; `41279617534` exposed an independent VisionConfig path; `41279755340` exposed a worker-pool binary default; `41279888248` needed explicit pytest-asyncio plugin loading; and `41280023388` needed the integration fixture temp-directory override. The final green workflow addressed these with configuration-only `/tmp` overrides and explicit plugin loading. The source candidate remained pinned and unchanged for the accepted run.

## Excluded local evidence

The old TU-ADV source preparation draft is preserved byte-for-byte inside `retained-failed-and-excluded-originals.zip`; it predates hosted acceptance and is superseded by `TU-ADV-1-SOURCE-CLOSEOUT-NOTE.md`.

The unadmitted direct local run reporting `42 passed in 4.22s` is excluded: it lacks captured invocation time, process closure, grant admission, CPU affinity, sampled RSS and drain receipt, and ran without the authorized R6 guard. Exact incident notes are in `EXCLUDED-LOCAL-RUN-INCIDENT.md`; do not credit it as an R6 result. The earlier intermediate 41-test log is retained under `attempt-intermediate41-no-final-receipt/` (SHA-256 `72aff757404342f16a0786dac0d62f6a06010f5225467962a733db1c4890d104`), but its original accepted R6 receipt was overwritten and cannot be recovered. Do not reconstruct it. The later local R6 refusal is preserved at `attempt-20261101T055114Z-2401742-36-37-refusal/receipt.json` (SHA-256 `6fac6c24d1d710aa05243bf0bd5194a2770033e6d3eb22b671a1addea9f07cae`); it refused before process start because the timing grant held CPUs 0–95. No alternate pair or bypass was attempted.

Hosted CI establishes deterministic source/test correctness only. It is not evidence of model quality, native security efficacy, deployed behavior, inference/performance, or global skill adoption.
