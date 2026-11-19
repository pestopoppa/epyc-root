# KPF-17.4d R6 build-only failure

`kvu-kpf174-custody-r6-20261119`: **build-only FAIL**, rc1. Neither
`RESULT.json` nor `CUSTODY.json` was produced. Ninja stopped at UI embedding:
`ui-assets.cmake:291` reported `llama-ui-embed failed (1)` because the UI
asset set lacked `bundle[hash].js`, `bundle[hash].css` and `workbox[hash].js`.
The first-object smoke does not establish full-build acceptance.

Native build log:
`/mnt/raid0/llm/tmp/heterogeneous-slot-fabric-residency/kpf174-build-r6-20261119/runs/build-2V7RWenI/build.log`,
SHA-256 `76fa1bd4ef25b11acf97e4807b2ca6402ee235aa7cfd1199aab063f9bd344383`.
End record: `/mnt/raid0/llm/tmp/compute-flags/grants/kvu-kpf174-custody-r6-20261119.ended`,
SHA-256 `690f683d5b3e8c5d912ff01a5b79b018ed1c3d72f4c0374ea28ce99f3949d4f3`.
The agent verdict is filed under
`/mnt/raid0/llm/tmp/compute-flags/filing-done/kvu-kpf174-custody-r6-20261119.verdict.json`.

Next: diagnose and repair the UI input preparation against the pinned source
and reference options, then publish a fresh successor with the four-CPU smoke.
Do not weaken the full-build rule or inherit the R6 smoke as qualification.
KPF-17.4d remains open; no inference or historical verdict changed.
[no-belief: build verification only]
