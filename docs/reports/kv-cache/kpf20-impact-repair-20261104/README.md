# KPF-20 captured argument-defect repair

The historical `kvfork20-p2-impact-20261102` run indexed its pinned
`488b31c96c6c148768508b3dcaefcb6c4c297664` checkout successfully in 65.2 s,
then failed its first `context acquire` call. The retained
`/mnt/raid0/llm/tmp/kvfork/kpf20-v3/out/context-acquire.stderr` reports multiple
registered repositories and asks for an explicit repository selector. The job
passed neither `--repo` nor a unique symbol UID. No context or impact record was
written. Its only JSONL record is a partial native member-call scan.

`job.py.patch` repairs the captured historical script; `repaired_job.py` is the
same repaired source for inspection. Both context and impact commands bind
`--repo` to the exact worktree path. Error, ambiguity, unknown risk, partial, and
truncated results remain failures. Completion gets an explicit non-partial
record after all target context/impact pairs and source checks finish.

This is a repair artifact, **not a runnable new row specification**. The embedded
historical worktree and HEAD are retained to make the diff reviewable. The
current handoff supersedes this source pin: KPF-20 is folded into KPF-22 and a
single lawful continuation must use a fresh private worktree at the resolved
orchestrator `origin/main`, indexed under its applicable claim. Preserve the
existing lineage and three-qualification-failure accounting; do not submit a
fresh row ID to bypass it. The parent must reconcile continuation admission and
re-resolve current symbols before adapting this patch into that continuation.
No new compute, qualification, or publication was run here.

HIGH/CRITICAL outputs still require operator warning before source edits; this
artifact changes only the scan driver, not any impacted production source.

Offline check:

```sh
python3 -m unittest discover -s docs/reports/kv-cache/kpf20-impact-repair-20261104 -p test_repair.py -v
```

Three tests pass. They exercise exact-worktree repository selection and
fail-closed result validation without invoking GitNexus or model inference.
