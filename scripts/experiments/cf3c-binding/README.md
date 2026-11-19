# CF-3c fixed binding diagnostic

`prepare.py` seals a separate 24-cell profile from the prospectively compiled
`cf3c-binding/cohort.json`, reusing the clean detached `cf3c-binding/source`
worktree at `12afe2858f9dbd4691447926d6cf1864de64348c`. It neither modifies nor
extends the earlier source-pool profile. The canonical cohort digest is
`14c79e10bade5909a5406b86ea72d91e44b66f830859044639b0c9c622cb5cc3`.

The packet contains this repository's experiment helpers and a pinned version
of its CMP4 serving harness. Existing model/build custody receipts and the
research repository's linkage verifier are referenced in place and checked
against pinned hashes. Preparation never hashes model weights. Runtime checks
bind the recorded model file identity, production binary/library digests and
chat template. No production process or kernel is modified.

The shared task-suite runner selects only `binding_deep_v1/A1-k12` for smoke.
Qualification requires an active first native policy receipt, a correct answer
to the masked receipt task, a real native retrieval call, ten source-written
archive observations, complete native token accounting, child exit and private
listener teardown. Native request capture validates selected-history custody.
The full row uses the fixed 24-cell schedule, with no replacements or retries.

Publish `packet/spec.json` through `publish_row.py`; only its allocator-owned
smoke runs in the owner turn. Official outcomes belong to CF-3c-B2 and are
separate from qualification. Four development tasks cannot establish held-out
quality or the parent's one-point adoption margin. Scripted archive creation
is excluded from continuation costs; the absent A3 carrier remains explicit.

The refusal controls in `test_profile.py` check paired cohort coverage, altered
archive/digest rejection and schedule tampering. The existing task-suite tests
cover native selected-history custody, source-log recovery and oracle isolation.

## Separately sealed recovery profile v2

`python3 prepare_v2.py` prepares `cf3c-binding-probe-v1/packet` without
changing the failed original packet. Publish its `spec.json` with
`publish_row.py --smoke-now`. One native qualification attempt is allowed.
The smoke runs only `native_recovery_control_v1`, seed 195981119, A1-k12,
with no quality grade. It qualifies actual returned archive text and its
source-written digest, active first-generation wire custody, complete costs
and child/listener teardown. Correctness and answer text cannot select PASS.
The probe module and flag are sealed with the profile. Native capture starts
before REPL construction so the tool namespace binds the observed peek.

Official execution retains the exact original 24-cell cohort and schedule;
it does not run the smoke control as a quality cell. The control OUTCOME,
usage and wall time remain separately identifiable in the smoke report,
with `quality_cells_observed=0`. Read the v2 smoke verdict separately from
any official result. No quality or adoption claim follows from qualification.

Offline validation in this host's split Python environments:

```bash
python3 -m pytest -q scripts/experiments/cf3c-binding
/mnt/raid0/llm/epyc-orchestrator/.venv/bin/python -c 'import sys; from pathlib import Path; sys.path[:0]=["/usr/lib/python3/dist-packages", "scripts/experiments/cf3c-task-suite"]; import prepare; prepare.SOURCE=Path("/mnt/raid0/llm/tmp/delegation-context-preassembly/cf3c-binding/source"); import pytest; sys.exit(pytest.main(["-q", "scripts/experiments/cf3c-task-suite/test_suite.py", "scripts/experiments/cf3c-task-suite/test_binding.py"]))'
```

The suite tests need the retained binding source because the historical
source-pool scratch tree can be reaped. This override uses the same pinned
orchestrator commit and changes no runtime packet. The v2 seal includes the
preparation-time helper bytes; its input digest identifies those exact bytes.
