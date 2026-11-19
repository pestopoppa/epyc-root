CAFE-4 corrected-source HIP R4 native controls
=============================================

Row `df2-cafe4-modes-native-hip-r4-20261119` requests exclusive GPU scheduling
for widths 2 and 3, normal rc0 PASS and explicit injected-fault rc1 FAIL.
The corrected-source HIP R4 executable is bound by SHA-256
`1623d9e2455116944e330a8c28200a84270f0dd0833563171f48344e22dfb63a`;
[build qualification](../cafe4-hip-build-r4/README.md#scheduled-build-verdict-2026-11-19)
binds source, patch, compiled markers, gfx90a and defined backend exports.
`inputs.json` binds the executable, all six local libraries and runtime files.
Model content verification is reused only with unchanged complete stat.
Small inputs and artifact hashes were checked before publication; the grant
performs no weight hashing or preparation.

The runner uses `-ngl 99` and a local `LD_LIBRARY_PATH`. Each native case must
show the model and all six expected llama/ggml libraries mapped, with no
foreign library, and two live samples of that child's KFD membership and
positive per-device VRAM. Samples retain PID, device bytes and observation
time. No sample after the child exits can establish residency. Smoke stops
cleanly after these mapping/residency witnesses; it proves no rollback result.

The fixed error tolerance is **0.743863867**, lower error is better. The
parser rejects a different tolerance. Reference floor stays separate; no
threshold search or relaxation. Each completed case requires native partial
acceptance, target modes1/2, rewind, finite nonfault errors within tolerance,
fault deltas over 10x tolerance, exact intended exit and result, no cutoff,
and a reaped child. Stop at the first failed/missing control (UNKNOWN), STOP,
deadline, or four valid cases (PASS). One frozen prompt, diagnostic acceptance
cap; no performance or general rollback claim. Official grant digest binds
scheduled results. Existing CAFE-4 source registration applies; producer is
not belief-wired.

Validation: **6/6 model-free tests PASS** including numeric/exit rejection,
fixed-tolerance enforcement, missing KFD, zero VRAM and foreign-PID rejection.

Publication on 2026-11-19 returned **GPU busy: smoke queued**. No smoke PASS
or native numerical verdict is claimed. The keeper will qualify it in a GPU
gap. CPU R2 native row was already qualified and remains pending.
Result path: `/mnt/raid0/llm/tmp/df2/cafe4-modes-native-hip-r4-20261119/RESULT.json`.
[no-belief: tested diagnostic runner and queued publication only]

Smoke launcher repair (2026-11-19)
----------------------------------
The first queued smoke failed before executing the payload: the engine rejected
exclusive GPU scheduling without an explicit CPU claim. Added
`--claim-cpus 184-191`, matching the row's GPU host region. The engine overrides
this with its assigned smoke CPUs under `FILLER_DRYRUN_ONE_QUARTER` / `FILLER_SMOKE`;
no engine or grant changes were made. Updated the input manifest's launcher hash.
Launcher SHA-256: `30d7991b5abe42a0ee37c76d85ecbdfe2deb296db7037f3bb6d6f6369f3d8af3`.
`bash -n` and all six model-free runtime tests PASS. Republication returned
**GPU busy: smoke queued**; qualification and native numerical verdict remain
pending. Alert `055639d1368b71ecaa53da40` acknowledged after repair.
[no-belief: launcher repair and model-free validation only]

Scheduled native verdict (2026-11-19)
-------------------------------------
`df2-cafe4-modes-native-hip-r4-20261119` ended **rc2 / INCONCLUSIVE
(UNKNOWN)** at 17:22:53Z. Width2 normal exited rc2 with `controls=null` and
`UNKNOWN lifecycle/provenance or matched-prefix control missing`. The
stop-on-first-missing-control rule prevented the other three cases. The log
contains draft-rewind and target-mode2 markers; it does not establish the
complete required lifecycle, matched-prefix, mode1 or numerical/fault controls.
The terminal message combines several predicates, so it does not identify
which predicate failed. No numerical error or tolerance comparison is available.

Model and all six expected local libraries were mapped. Two live samples
for child PID 3689318 show KFD registration and **37,525,798,912 VRAM bytes**
each. No cutoff occurred and the child was reaped. These residency witnesses
do not establish rollback correctness. Fixed tolerance **0.743863867** remains
unchanged; no performance or full CAFE-4 claim follows. The parent stays open.

Evidence is referenced in place, not copied:

- Result: `/mnt/raid0/llm/tmp/df2/cafe4-modes-native-hip-r4-20261119/RESULT.json`, SHA-256 `1045655f3c5f22bbd8e525eac0f26e4e3aa2ca56008200bc8c0717684fc19bf4`.
- Native log: `/mnt/raid0/llm/tmp/df2/cafe4-modes-native-hip-r4-20261119/runs/84224bb656e942e0b69274c3ab188544/width-2-fault-0.log`, SHA-256 `d65ae64103b6bf6213c9f9ce5e91363bbd03f577a006d2c70c872c595d1628fc`.
- End record: `/mnt/raid0/llm/tmp/compute-flags/grants/df2-cafe4-modes-native-hip-r4-20261119.ended`, SHA-256 `f5b4617e7a83b322f964b5fe6b765029e90f906132bf173f0fc49f6d66a0f9ec`.
- Qualified executable SHA-256 remains
  `1623d9e2455116944e330a8c28200a84270f0dd0833563171f48344e22dfb63a`;
  corrected source SHA-256 remains
  `41fc473a908b7c385d79d1941b6576cc993b985e691682d6598d6122e968fe1c`.

Next: distinguish the combined native failure predicates with model-free
regression coverage before publishing a replacement build/native row.
CPU R2 native row remains independently queued.
[no-belief: inconclusive single-prompt diagnostic; existing producer not belief-wired]
