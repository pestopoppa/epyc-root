# 2026-10-28 — HIL shared orchestrator-venv incident checkpoint

## Problem and attribution

HIL-15 discovery shard s1 refused to start unit 03 at 02:01:08 UTC with `Python runtime source tree changed`. Its runtime audit shows that the shared orchestrator venv changed at about 01:54:58 UTC, during s1 unit 02 replay 2. The precise M4 preparation capture now identifies the operation responsible: `command.txt` in `scope-check/20261028T015457Z-2658028/` records the authorized invocation of `/workspace/.claude/skills/kernel-promotion/scripts/scope.sh --backend cpu --json .../scope-cpu.json`; the paired `command.log` reports `Building epyc-orchestrator`, `Uninstalled 1 package`, and `Installed 1 package`. The log SHA-256 is `fa5466ceda05d6a45577bb48213d8664d068ed7de178991896e6d21ecf7d277e`.

The captured PID `2658028` is the helper PID only; no installer PID is asserted. This operation is the identified source of the shared editable-install mutation. The incident audit measured eleven changed editable-install metadata files, changed `METADATA`, `RECORD`, and `uv_cache.json` bytes, and an unchanged `.pth` byte stream with a changed inode. These changes coincided with the original runtime refusal. The evidence does not determine whether the mutation affected replay 02-2.

## HIL evidence preservation and containment

Original s1 units 01–02 contain six completed native slots (unit 01 pass/pass/pass; unit 02 fail/pass/pass); units 03–15 have 39 unstarted slots. Original source, receipts, and partials remain untouched. No old capsule was rearmed, no completed slot was redrawn, and no no-impact conclusion is made. The owner prohibited future writes to `/mnt/raid0/llm/epyc-orchestrator/.venv`; tests and installs must use private environments. The private-runtime v5 continuation uses distinct capsules, confines runtime imports to a retained private runtime, and limits s1 to units 03–15. Its fresh row preflights passed and the owner subsequently armed the v5 shards. These repairs do not produce a HIL outcome or adjudicate the 02-2 overlap.

## Files and verification

| Artifact | Change / result |
|---|---|
| `handoffs/active/refactoring-multirepo-2026-10.md` | Added one root-owned HIL incident-attribution child checkbox with `[no-belief: incident attribution and runtime repair only; no HIL outcome]`. No peer checkbox changed. |
| This per-agent progress shard | Preserves attribution, PID boundary, slot inventory, unknown overlap, and owner containment rule. |
| `/mnt/raid0/llm/tmp/refactor-01a16fc3/compute-coordination-20261026/HIL-VENV-INCIDENT-ATTRIBUTION.md` | Source attribution and owner rule. |
| `/mnt/raid0/llm/tmp/refactor-01a16fc3/hil15-runtime-fix/INCIDENT-AND-RESUME.md` | Runtime refusal, slot accounting, preserved evidence, private continuation and remaining uncertainty. |
| `/mnt/raid0/llm/tmp/refactor-01a16fc3/m4-full-fold-ready-20261028/scope-check/20261028T015457Z-2658028/command.{txt,log}` | Exact authorized helper invocation and package rebuild/uninstall/install output; helper PID is not attributed to the installer. |

No model or GPU work was run for this checkpoint. No source code, HIL enrollment/source artifact, index row, or shared orchestrator venv was changed. The native s1 continuation outcome and determination of replay 02-2's overlap effect remain open.

Documentation and wrap-up checks: `git diff --check` passed; `check_readme_freshness.py` completed without warnings; `scripts/handoffs/index_state.py` regenerated successfully under the wrap-up lease and `--check` exited 0 with 0 problems. Its advisory output named two legacy `/running` scratch warnings and 129 handoffs without a `Scratch` field; none concerns this checkpoint. `scripts/vidya/cli.py sync --check` reported `ledger FRESH`, 2491 entries through `intake-2510`, lag 0. The handoff diff adds exactly one completed child checkbox with its no-belief reason; no other checkbox was changed. No new follow-up task was discovered. This per-task wrap did not run operator-cadence index pruning or the wiki compilation sweep.
