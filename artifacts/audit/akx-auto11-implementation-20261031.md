# AKX-AUTO-11 implementation audit — 2026-10-31

MAIN accepted closing the original implementation checkbox only. The separately listed non-DS41 live exercise and CH-27 remain open. No source change, new floor, production change or duplicate READY packet was needed. [belief: cc]

Research source audited from fresh `origin/main` git objects: `d1c7a8ffb9389b71d88b453d26c6c506346311e2`. Shared source working trees remained read-only.

The adopted 2026-10-22 registry contract keys execution equivalence: source tree excluding tests/docs, raw CMake recipe and compiler. It records the actual measured execution digest, executable and DSO hashes. This permits the already-authorized equivalent rebuilds without using a tree label as identity. The master `orchestration/model_registry.yaml` is the only floor store; registry claims are calibration locks.

Actual caller resolution in `scripts/kernel_rnd/autokernel/loop/`:

- `floor_registry.py:597` plans sealed, durable native-record registration and pins its bytes and actual build identities; scratch records are refused.
- `floor_registry.py:880` (`check_launch`) looks up before claiming calibration, returns reuse on a hit, refuses stale anchors, and atomically excludes a second calibrator.
- `run.py:1654` calls `_registry_floor_reading` before calibration; its reader at line 1746 resolves the selected build, current champion and matched recipe/request/model/frame/pairs/epoch/grade. Store attestation is at line 3302; long-context lookup is at line 7855.
- `champion_reanchor.py:488` calls `check_launch` on the actual apply path and forwards the selected store image and registry arguments through its SPEC.

The master contains one registered role, historical DS41-1017 on `dd3d9721ca37321ad9159520bbd9616e3d0d6228`, execution digest `c70c8066c533d0cdf93daa117a9919f34dc561cc0938e966ce544e8d94d54dbb`. Its durable native record exists and matches its registered SHA-256. Its 2.862% floor is not relabeled as current C5. No Q38FN entry exists.

Bounded execution of existing floor-registry tests returned **5 passed, 10 failed, 1 deselected**. Each failure was the intentional durability refusal for synthetic test records under the only authorized scratch path. The deselected test imports the full runtime package, absent from this partial-object audit extraction. No full-suite pass is claimed; no production guard was weakened and no fixture was moved outside authorized scratch. Passed checks cover equivalence, changed source/flags/compiler, thread mismatch, stale-anchor refusal and store-image recognition. The monitored test batch used OMP1/SMT130-131 under the 34-35 mutex beside correctness grants: 1.72 s, peak sampled RSS41,091,072 bytes, 7 samples. The 10 refusals remain recorded in scratch `validation.log`.

GitNexus reported LOW impact (2 upstream nodes) for `check_launch`. Its shared index describes stale shared HEAD `99301fa`; fresh git-object caller inspection above supplied the actual re-anchor caller missed by that index. No re-index was run.

The existing `codex-ni-ch27-c5-raw-recalibration-20261030` READY packet remains the live exercise path: original Q38FN raw-C5 A/A, 24 pairs/48 launches, 5 comparison pairs, t48, whole-host 0-95 and exclusive GPU quiet, 200 GiB, 5700 s with 5400 s minimum. Its 46.005 s derivative smoke is expressly nonadmitted; it establishes no floor. Existing predeclaration and launcher ownership remain unchanged. DS41 QKV qualification is a different model/workload and cannot establish this exercise; its owner confirmed independence. No new measurement warrant is asserted.
