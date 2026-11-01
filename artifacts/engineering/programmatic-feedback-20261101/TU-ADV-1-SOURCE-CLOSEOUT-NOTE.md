# TU-ADV-1 supporting source evidence — partial, 2026-11-01

This note supplements the existing checked `TU-ADV-1-SOURCE` line and its original 2026-10-06 6/6 evidence; it does not rewrite that task text, create a new checklist item, or close the parent `TU-ADV-1` task.

## New source boundary

APP source commit `f6b648dd5167465df82cd327437502e6aeacbacc` adds a native evaluator-provenance bridge at the real `DistillationPipeline`/temporary `SkillBank` admission boundary. It reopens the pinned native contract and immutable trace before teacher/store use. Explicit malformed, unknown/unsupported, failed, mismatched, or unverifiable provenance is rejected. No-provenance legacy inputs retain their prior UNKNOWN behavior. Temporary SkillBank fixtures exercise this boundary; they do not establish global persistence or adoption.

Source path hashes at the accepted TU-ADV source revision:

| APP path | SHA-256 |
|---|---|
| `scripts/autopilot/evals/dtap/harness/runner.py` | `4470e66f28144d5f4c187bcc54a02d7269eb5948c807a60e2fc66cfaa62393e5` |
| `orchestration/repl_memory/distillation/pipeline.py` | `9b08db70c9a4a68d4a86d73970f7f7c97fb8fe58bc052e5bd957cacdc2cba98f` |
| `scripts/skillbank/seed_skills.py` | `26e035d28f8d3dfc5b6d525f89237f46d24ed5c7a7d69b06478f159b6ea0ea62` |
| `scripts/autopilot/evals/dtap/tests/test_adversarial_contract_fixtures.py` | `713415f37b0356aa62afc1afa3e8a172341e988b2efffc7fc3000c1b18ccd3bf` |

These hashes are also entries in the full 17-input hosted source manifest at `hosted-run-41280199807/source-files.sha256`; the run source identity is candidate `ac48a632af48e6cfc0ac52e08afb585aad16c596`, later promoted to APP main in merge `f6dff34eb244b3cf3ad99f027b40a583f2393da1`.

Hosted run 41280199807 passed the feedback, distillation and full DTAP contract test set (214 passed, one existing warning). This is deterministic source/test evidence only.

## Remaining parent scope

The parent task remains open for the exact external Continual/Pokee cases and global cross-run skill-persistence acceptance. This bridge does not claim those cases, general attack-surface coverage, model efficacy, live security behavior, deployed behavior, or cross-run adoption. Retain the original checked source item's 2026-10-06 6/6 as historical; it is not retroactive evidence for these new source checks.
