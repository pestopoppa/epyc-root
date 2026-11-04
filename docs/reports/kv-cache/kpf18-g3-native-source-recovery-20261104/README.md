KPF-18 G3 native-source custody report v3

Audit scope: all entries in the candidate NATIVE-SOURCES.sha256, with focus on the four present-but-mismatched external scripts and the missing README. Candidate files were not modified. No model/build/GPU work or publishing was performed.

Exact README recovery:
- Required SHA-256 `a5fd06aacbe0853784fe2201a337b5d626e9021960800c573ce6815518ae6453` exists in root Git history at commit `8a640317ed024745f294d11c5c88887270fddd07` for `scripts/vidya/adapters/README.md`.
- The same exact bytes were found in retained file `/mnt/raid0/llm/tmp/codex-ni-20261027-inf75-census-prep/root-native-census/scripts/vidya/adapters/README.md` and staged under `relocated/canonical-export-root/scripts/vidya/adapters/README.md`. The nearby r15/r16 copies are different and were not used.

Four present-but-mismatched external source files:
- `region_lock_cli.py`: expected `58c2ea675db751f7403222ebbb3d6e52a4ce151ade86035e00fddda411b69940`; exact Git blob recovered from `epyc-orchestrator` commit `9dbcc8fb17427320a3d0a7815b00e62f29aa0c35`.
- `cpu_region_lock.py`: expected `24a4a377fe5050e0f34514294e7d14bcc94db4c99fe89b91881d68ae81ece56c`; exact Git blob recovered from `epyc-orchestrator` commit `11e6d867890952c01bcad367e931f86f5520df02`.
- `grant_ok.sh`: expected `6a2467d67da413bf12a702a731b0b11f5715e01a5143584dc6df47761788ebba`; exact retained baseline recovered from `/mnt/raid0/llm/tmp/codex-ni-20261026-launch-admission-gate/baseline/grant_ok.sh`.
- `grant_ok_launcher.py`: expected `ba15f29581e75d74926d0ba687a9b798b1cb4527633aef1a03810268b16d3b5d`; exact retained baseline recovered from `/mnt/raid0/llm/tmp/codex-ni-20261026-launch-admission-gate/baseline/grant_ok_launcher.py`.

These are source files, not volatile executable payloads. The recovered historical bytes establish source identity only; they do not authorize invoking obsolete lock or grant scripts for current resource admission. A prospective entry must use the current official rowflow and lock lifecycle and verify its own bindings.

All staged recovery items:
- `58c2ea675db751f7403222ebbb3d6e52a4ce151ade86035e00fddda411b69940` `/workspace/repos/epyc-orchestrator/src/runtime/region_lock_cli.py` → `/mnt/raid0/llm/tmp/heterogeneous-slot-fabric-residency/g3-native-custody/relocated/external/region_lock_cli.py`
- `24a4a377fe5050e0f34514294e7d14bcc94db4c99fe89b91881d68ae81ece56c` `/workspace/repos/epyc-orchestrator/src/runtime/cpu_region_lock.py` → `/mnt/raid0/llm/tmp/heterogeneous-slot-fabric-residency/g3-native-custody/relocated/external/cpu_region_lock.py`
- `5602e0de1c49ccdb4b5ea82adb8d45b16dc32ebb4111bed9ccdf2c55ec7d8306` `/mnt/raid0/llm/tmp/codex-ni-20261027-kpf18-r15-repair/successor/gate/filler_run12.sh` → `/mnt/raid0/llm/tmp/heterogeneous-slot-fabric-residency/g3-native-custody/relocated/gate/filler_run12.sh`
- `aa9ed900be5fb7f3efca043bfddb2ac8963964710db0b702c7491729a74f8542` `/mnt/raid0/llm/tmp/codex-ni-20261027-kpf18-r15-repair/successor/gate/dryrun_check.py` → `/mnt/raid0/llm/tmp/heterogeneous-slot-fabric-residency/g3-native-custody/relocated/gate/dryrun_check.py`
- `b38c9804952017e9b158cf1d5310c8987ab2753132dcb5ec77fb2534502b66ab` `/mnt/raid0/llm/tmp/codex-ni-20261027-kpf18-r15-repair/successor/gate/dryrun_disk_policy.json` → `/mnt/raid0/llm/tmp/heterogeneous-slot-fabric-residency/g3-native-custody/relocated/gate/dryrun_disk_policy.json`
- `6a2467d67da413bf12a702a731b0b11f5715e01a5143584dc6df47761788ebba` `/mnt/raid0/llm/tmp/compute-flags/grant_ok.sh` → `/mnt/raid0/llm/tmp/heterogeneous-slot-fabric-residency/g3-native-custody/relocated/external/grant_ok.sh`
- `ba15f29581e75d74926d0ba687a9b798b1cb4527633aef1a03810268b16d3b5d` `/mnt/raid0/llm/tmp/compute-flags/grant_ok_launcher.py` → `/mnt/raid0/llm/tmp/heterogeneous-slot-fabric-residency/g3-native-custody/relocated/external/grant_ok_launcher.py`
- `e6ead7b654defc820abefb71b997c12b93b49bc1dc0ac036e2b5e72b50b4895d` `/mnt/raid0/llm/tmp/codex-ni-20261027-kpf18-r15-repair/successor/canonical-export-root/scripts/vidya/adapters/kv_prefix_fork.py` → `/mnt/raid0/llm/tmp/heterogeneous-slot-fabric-residency/g3-native-custody/relocated/canonical-export-root/scripts/vidya/adapters/kv_prefix_fork.py`
- `6ae969f7029c1a6356593fd2432eca2320931f22aa4a8c4e3a388a72b81944e7` `/mnt/raid0/llm/tmp/codex-ni-20261027-kpf18-r15-repair/successor/canonical-export-root/scripts/vidya/claim_tuple.py` → `/mnt/raid0/llm/tmp/heterogeneous-slot-fabric-residency/g3-native-custody/relocated/canonical-export-root/scripts/vidya/claim_tuple.py`
- `cda6809d24382cbbfa80308c9f8df4eca353f458039816753b1c20156adf1434` `/mnt/raid0/llm/tmp/codex-ni-20261027-kpf18-r15-repair/successor/canonical-export-root/scripts/vidya/canonical.py` → `/mnt/raid0/llm/tmp/heterogeneous-slot-fabric-residency/g3-native-custody/relocated/canonical-export-root/scripts/vidya/canonical.py`
- `a5fd06aacbe0853784fe2201a337b5d626e9021960800c573ce6815518ae6453` `/mnt/raid0/llm/tmp/codex-ni-20261027-kpf18-r15-repair/successor/canonical-export-root/scripts/vidya/adapters/README.md` → `/mnt/raid0/llm/tmp/heterogeneous-slot-fabric-residency/g3-native-custody/relocated/canonical-export-root/scripts/vidya/adapters/README.md`

Verification result: all 11 non-matching/missing manifest entries now have a staged exact-digest copy. The 4 mismatches were classified as source drift; no current volatile executable is being treated as historical evidence. Original candidate manifest and its path entries remain unchanged.

A subsequent byte-only verifier binds the relocation map to the original manifest digest and refuses missing or changed bytes, unknown or duplicate mappings, noncanonical path aliases, symlink aliases and escapes. Twelve synthetic tests pass. Its original scratch run verified all 52 manifest entries, 11 through explicit relocations; it executed none of the recovered files. The verifier, tests, map and original manifest are retained here; relocated bytes remain under the scratch path listed above. This does not bind the current runtime to those bytes or qualify a launcher.

Retained SHA-256 bindings: native manifest `50e1499b9a82fc83a7cdcb1415d543598915217cb9aef1798ce3270815763f4e`; relocation map `7c8bd8d03af6c2757350605912204cad45341a3d2e919b68a77de2c66ccabb91`; verifier `adfbd9005187f454cb10e1f6a1a8d5bc55109145480ee9153c404c187a1ae938`.

The candidate's `guard.sources()` also checks the separate R9 validation `NATIVE-SOURCES.sha256`. A later read-only check found four failed paths there: the same changed `region_lock_cli.py` and `cpu_region_lock.py`, plus missing R7 and R8 `evidence_view.py` files. The 52-entry result above applies only to the candidate's native manifest; it is not a full `guard.sources()` pass. The R13 data and R9 local source manifests showed no failed entries in the same check. Recovery of the two additional readers and binding of both manifests remain required.

A scoped search for the two R7/R8 readers found neither exact digest among retained files with that name under the searched temporary, worktree and workspace paths, nor in the current root repository's reachable Git objects. Nearby R5/R6 and R9 copies have different digests. `R7-R8-RECOVERY.txt` records the search and limits; it does not establish absence from every possible archive. No historical source or guard was substituted.

A concurrent KPF session subsequently recovered both exact readers under different retained names, resolving the scoped search above: R7 is `/mnt/raid0/llm/tmp/kvfork/r9-recovered/codex-ni-20261027-kpf18-format-r7/evidence_view.py`; R8 is `/mnt/raid0/llm/tmp/kvfork/g3-r9-validation-inputs-20261104/r8-evidence_view.py`. Both match their original digests and appear in the independent R9 successor inventory. [Independent custody and limits](../kpf18-g3-provider-transport-prep-20261104/README.md). This is source custody only; it does not qualify the candidate or authorize old runtime guards.
