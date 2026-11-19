# KPF-18 group-3 provider/transport successor preparation

The initial v2 preparation was created at `/mnt/raid0/llm/tmp/kvfork/g3-provider-transport-prep-v2-20261104` and later removed after the independently verified R9 successor below superseded it. The available final preparation is `/mnt/raid0/llm/tmp/kvfork/g3-provider-transport-r9-prep-20261104`. It copies the pinned private runtime, applies the bounded seed-transport patch, installs its socket watchdog, copies the reviewed current-provider witness and reviewed source map, replaces the historical lock adapter with an exact successor-row adapter, and invokes that adapter at every `guard.boundary()` call. Both the outer default/official/normal/cutoff entry and the inner runtime launcher refuse with rc78. No grant, row, model, GPU request or inference was executed. NI's packet, predecessor launchers and source inventories remain unchanged; R15 remains INVALID.

The provider-source map is independently pinned to SHA-256 `75d470545c780089bb4bf2e5492e3036b77ea51a8cb12ed50fb6f311011932ab`, never freshly enrolled from live source at entry. Its five current orchestrator source identities matched during preparation. The exact planned row is `kpf18-g3-provider-transport-prep-20261104`; absent/wrong `FILLER_ID`, nonmatching provider request tag, writer loss, stale attribution or source drift refuse. This is prospective source integration, not an actual enrolled rowflow entry or an observed authorized provider witness.

All 79 copied/integrated runtime files are covered by the outer complete inventory, along with the receipt, patch and 52-entry external native inventory: actual entry verification passed 133 entries. The copied runtime has a regenerated `SOURCES.sha256`; bootstrap tools, exact expected path list and inventory are sealed before custody verification. The pinned predecessor runtime inventory was `04c0d3922939496fb100b0a7b0a0efe228ee7f3611ad025cc6d47d3c8bb684f7`. Its missing `fork-launch-native.raw` was recovered solely from retained `g3-custody/candidate/fork-launch-native.raw` with the original inventory's exact SHA-256 `192c06830316e13c0b86df1c3167aa653667f161ff966ec2d80694d26eb93689`. No replacement bytes were invented.

Five focused integration tests pass: both barriers/custody; patched transport and boundary wiring; source mutation plus incomplete refusal; reviewed-pin/destination/inventory rejection; exact-row adapter ownership and writer-loss refusal. The existing eight real socket/output tests also pass. These are model-free controls. Recheck the available final successor with `bash /mnt/raid0/llm/tmp/kvfork/g3-provider-transport-r9-prep-20261104/launch.sh custody-check`. Test commands:

```
PYTHONDONTWRITEBYTECODE=1 python3 -B -m unittest discover -s scripts/coordination/kvfork/kpf18-g3-successor -p 'test_*.py'
PYTHONDONTWRITEBYTECODE=1 python3 -B -m unittest discover -s scripts/coordination/kvfork/kpf18-g3-supervision -p 'test_*.py'
```

Remaining admission/integration work is explicit and keeps the barrier closed:

- Official current rowflow launcher, grant/STOP/deadline and terminal lifecycle must be integrated; the adapter itself supplies no grant or row enrollment.
- Historical config, launcher/bootstrap assumptions and hardcoded old grant identities still need current-entry integration. The inner runtime entry deliberately has no dispatch tail.
- Current rowflow's four-CPU smoke must replace the retained `{184,185}` requirement without bypassing resource/admission checks.
- Independent validation-manifest custody remains incomplete.
- Disk admission is 214 GiB (150+64); current `df -BG` reports only 165G available. The floor is unchanged.
- Native task cancellation/release and the complete GPU qualification remain unproven. Completion-socket shutdown alone does not establish task release; separate slot queries and filesystem operations remain outside the transport bound.
- Whole-attempt cleanup, process-group/adopted-child handling and sampled output overshoot remain unqualified; no quota or bound on cleanup latency is claimed.
- Own-process KFD/VRAM residency and actual GPU binding must be proven. Retained supervision reads fixed `card2`, which does not establish the current assigned device.

GitNexus status reported this working tree unindexed and impact could not resolve this lane, so no graph-verified blast radius is claimed. Changes are a new preparer/tests and a disabled scratch artifact, with no production serving mutation.

Historical v2 scratch pins (removed; final successor pins below):

- `launch.sh`: `4062bf2f20085ac08a03a6b239d1e04ae477b8089f388f537ce5135020b38908`
- `ALL-SOURCES.sha256`: `564f18330d2d68031ef396229d2b42f64b475f0c117f1d182d8a6632e314444c`
- `BOOTSTRAP.sha256`: `26e706ab778e6d4f7ab7edd07afa193e2a4e5b9b1499d9e213ae5e97aa14467c`
- `PREPARATION.json`: `28da0fb8cb910ba3a611f22737d8e5166366c792f2278aef7e1097182b2f9500`

The superseded initial same-day scratch copy was removed after v2 validation; it supplied no unique evidence. The v2 successor was also removed after confirming that the final R9 successor has no references to it; the final R9 successor remains disabled and retained. No generated candidate files are stored in the lane.

## Independent R9 custody integration (same-day successor)

The current disabled preparation is `/mnt/raid0/llm/tmp/kvfork/g3-provider-transport-r9-prep-20261104`. It supersedes the v2 preparation above only by adding independent R9 custody. After the independent owner completed all three closures, the preparer pinned that owner's `RESULT.json` to `72cdb01f1a53e51fa3810c6e46efd46892d1923ba0d760ffcb4a2a3f2a61d8f5`, rechecked the original R9 manifest pins and all 29+14+22 members, retained the receipt, and included its independent manifests, originals and member paths in the complete entry inventory. This closes the independent-validation-custody item above; it does not rerun R9 tests or establish runtime readiness. The historical R9 closure remains separate from the successor native inventory.

Actual entry custody passes 192 unique pinned entries. Normal entry verifies those entries then refuses rc78; the inner runtime barrier remains unchanged. The five existing integration controls passed after this preparer change. One additional focused test, `IndependentValidation.test_reviewed_r9_closure_and_refusals`, passes against the independently reviewed result and covers receipt pin drift, missing closure, manifest drift and incomplete-marker refusal. No broader suite was repeated for this final test addition.

The new `PREPARATION.json` SHA-256 is `f6919974801c9d1b972af12b568cbcb0f39196d9b4e91907b4e0867729719e70`; `ALL-SOURCES.sha256` is `01c6ac4303fb042e7876d858789aa5005e8d89ff61b78c1c1a3cc1ccc34fd963`. All other remaining admission/integration items above still apply. No row was published, no NI source changed and no inference executed.

## Current rowflow and residency preparation

The disabled `/mnt/raid0/llm/tmp/kvfork/g3-rowflow-prep-20261104` adds source-level current rowflow and four-CPU smoke checks. Its custody entry verifies 199 members; its outer, inner, rowflow, precondition and completion entries all refuse with rc78. Fourteen successor tests passed. The separately tested `scripts/coordination/kvfork/kpf18-g3-gpu/` hook prepares per-process KFD, mapped-HIP and VRAM evidence with dynamic device discovery; it is not installed in this candidate. Eight focused GPU-witness tests passed without inference. Its native writer/projection and planning canary remain pending under VB-KVU-PF.

These source checks do not qualify the actual publisher's lock or GPU admission, native cancellation and cleanup, sampled-output overshoot, or the disabled candidate. The 214 GiB disk floor remains in force. No G3 row, GPU run or gate verdict follows.
