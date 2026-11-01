# AK-INST-3 current audit (2026-11-01)

## Task identity and acceptance

`handoffs/active/autokernel-restart-and-strip.md` § AK-INST-3 says AK-INST-1's lineage helper is fixed and unit/mutation-tested, but no campaign has reached a scientific attempt. v37 stopped before the champion was finalized. Acceptance is a champion-instrumented campaign passing preflight and banking a real screen (`sci >= 1`); a dry run, synthetic fixture, READY packet, or old campaign result does not satisfy it.

## Fresh source and static lineage

- Research `origin/main`: `aa2143357d5382934580bcab6744b87b5fd1a6d4` (2026-11-01).
- `scripts/benchmark/run_autokernel_gpu_discovery.py` is byte-identical between the shared checkout and fresh origin. Its `_descends_from_reviewed_instrument()` helper accepts the exact reviewed instrument or a Git descendant; `preflight()` calls it on both the requested instrument and anchor build. It also pins the ready/continue contract SHA `1411f5e81c1b0b3db6952523922c672d88a78aaff5945865c9ccc2b4fc5fd99f`.
- Current C5 champion source `c72ec82f5417bb2937310326120f149b665e8400` descends from reviewed instrument `5bbcc5498e4732162356953b7be96a53073a6706` (`git merge-base` returns the instrument commit). The C5 commit's `tests/test-autokernel-ready-continue-contract.py` SHA-256 is the pinned `1411f5e8…fd99f`.
- Existing `ReviewedInstrumentLineageTests` cover exact instrument accepted, champion descendant accepted, and frozen production v9 refused. Earlier acceptance note records 56 tests passed for AK-INST-1. No source defect was found to fix.

## Latest witness and supersession

The read-only 2026-10-29 lineage audit records v37 stopped, exit 143, `scientific_attempts=0`, instrument commit `270b48ed64d617db9128054f3bd0620bbb9371f5`, production base v9 `0db32c06e3e550065b78311a6031ef3dd2c4f27c`. Its `state.json` SHA-256 remains `1f20995b0c54b632208f83bf83117012ed3e235d0bfbaa8b3d0de94279289bbd`; current read still reports `scientific_attempts=0`, `iterations=[]`, updated 2026-08-28. The previous `v19/v25/...` campaigns predate the champion lineage gate, and the unrelated later measurement has a different route/build scope. None closes AK-INST-3.

Current champion is C5 `c72ec82f5` (not v37's v9 anchor). Current CH-27 handoff reports its separate bounded Q38FN floor window aborted at precheck with zero floors; CH-27a remains to repair the recipe digest. That work is not a discovery campaign and cannot count as the AK-INST-3 witness.

## GitNexus and remaining boundary

`gitnexus impact _descends_from_reviewed_instrument --repo epyc-inference-research --direction upstream --summary-only` reports LOW risk, 5 impacted nodes; direct caller is `preflight()`. `gitnexus context` confirms the runner-local call flow. Index is current only to local checkout commit 99301fa (10/28), while origin is aa214335; runner source is byte-identical to origin, but impact counts are provisional until a fresh index is built.

The active champion handoff carries an operator hold: “DO NOT LAUNCH AUTOKERNEL”; the only named exception is one bounded CH-27 floor recalibration window. A scientific AK run is outside that exception. Therefore the exact unsatisfied dependency is a direct operator instruction lifting the AK launch hold for workspace-58 and assigning the campaign owner/window. No launcher, campaign state, grants, process, store, or source files were created or changed here. Do not mark AK-INST-3 validated until the required real C5 screen exists.
