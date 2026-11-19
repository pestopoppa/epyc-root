# KPF-41 precondition environment repair

The backend qualification smoke failed before its first work unit because the
launcher precondition invoked `job.py --check` without `FILLER_ID`. The rowflow
engine exports job variables later, when launching the job; preconditions run
before that export. The precondition printed successful manifest checks first,
so the engine's one-line refusal reason hid the later KeyError.

The source-bound launcher repair explicitly supplies the literal row identity
only to the custody-check command. The regular job command, runtime manifest,
binaries, source checkout, parser, GPU witness and decision rule are unchanged.
The old launcher digest and final digest are in `qualification.json`. No fleet
engine, grant or READY manifest was edited. This repairs the retained launcher
owned by `h-heterogeneous-slot-fabric-residency`, whose handoff is now routed to
kvu. The source-custody check remains strict; there is no environment fallback.

Three regression controls passed in 0.221 seconds. The actual precondition from
the predecessor reproduces `KeyError: 'FILLER_ID'` with the variable removed;
the repaired precondition succeeds in the same environment; source drift is
refused. These execute the real five-artifact/source/linkage custody check,
without launching the corpus or GPU witness.

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -B -m unittest discover \
  -s docs/reports/kv-cache/kpf41-precondition-env-20261119 \
  -p test_repair.py -v
```

The installed launcher is at
`/mnt/raid0/llm/tmp/heterogeneous-slot-fabric-residency/kpf41-backend-gpu-qualification-r2-20261119/launch.sh`.
Republishing its existing spec returned **GPU busy: smoke queued**. No smoke
PASS, readiness or corpus verdict is claimed. Alert
`21b55164dfcfe04c13d55d63` was acknowledged after repair and republication.
The old FAIL file was removed by republication; the regression test reproduces
the underlying defect directly. The dispatcher resumes on the queued smoke
result; no queue polling is needed.
GitNexus is unindexed in this lane, so graph blast radius is unknown; the change
is confined to one scratch-launcher precondition plus this source-bound repair
and its regression tests. KPF-18 driver integration was not changed this turn.
