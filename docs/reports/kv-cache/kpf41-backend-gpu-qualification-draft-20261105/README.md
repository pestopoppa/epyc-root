# KPF-41 GPU backend qualification: r3 parser repair

The r2 result remains **INCONCLUSIVE**: its backend exited 0 but interleaved HIP diagnostics broke parsing before post-run custody. See [the filed r2 result](../kpf41-backend-gpu-r2-result-20261119.md).

`corpus_parser.py` now recognizes only the exact graph warmup complete/reset messages, tracks a pending case until an explicit status arrives, and rejects malformed, missing and orphan statuses. `job.py` is safe to import for testing and records post-run custody in a `finally` block around parsing. Source, five artifact digests, explicit loader environment, live owned-PID HIP mapping and VRAM, cleanup and summary gates remain required. The successor source worktree is detached at `15caecbbf4cb27452dbd87fa1a68a0e75098388e`; no kernel source or build was changed.

Six offline tests pass, including 14 synthetic refusal controls, retained-log positive and two retained-log refusal controls, and post-run custody success/failure checks. The retained log is read in place and hash-bound, never copied. Replay reconciles 5,207 selected = 2,978 supported OK + 2,229 unsupported, with all 25 required shared-trunk cases OK and 212 allowed graph diagnostics. This does not repair r2's missing contemporaneous custody or qualify the backend.

Run the offline replay from the lane:

```bash
PYTHONDONTWRITEBYTECODE=1 KPF41_RETAINED_LOG=/mnt/raid0/llm/tmp/heterogeneous-slot-fabric-residency/kpf41-backend-gpu-qualification-r2-20261119/out/corpus.log python3 -m unittest discover -s docs/reports/kv-cache/kpf41-backend-gpu-qualification-draft-20261105 -p test_corpus_parser.py -v
```

`spec.json` and `launch.sh` now describe `kpf41-backend-gpu-qualification-r3-20261119`. The publisher smoke includes synthetic parser controls, bounded owned-descendant cleanup and the unchanged hash-bound 192 MiB HIP witness. Full corpus execution requires a keeper grant. A qualification PASS requires fresh before/after source, artifact and loader custody plus live residency and reconciled corpus. GPU correctness here does not establish direct-row dispatch, performance, serving or promotion.
