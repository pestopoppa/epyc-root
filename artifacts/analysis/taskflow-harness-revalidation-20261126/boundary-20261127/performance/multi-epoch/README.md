# A3B multi-epoch performance snapshots

`INPUTS.json` binds the serving roots, worker layouts, approved plans, coordinator seals, and configuration evidence for cache-safe-01, repaired CPU measured-01, and legacy GPU gpu-01. Reported paths and hashes refer to source evidence. The collector neither copies whole traces nor prints model bodies.

Generate a fresh snapshot from this directory.

```bash
nice -n 19 taskset -c 180-183 /usr/bin/python3 -B collect_multi.py \
  --input INPUTS.json --out "$PWD/snapshot-02"
```

Use a new snapshot directory for later observations. Planned units, in-flight archives and nonfinal results stay visible. All models are external to this collector. The snapshot reads independently appended prefixes, so a late receipt may appear on the next refresh.

Both supported wire locations and any identical copied receipt are recorded. Count a receipt once across phases. Hash-verified continuation ancestry keeps the old phase and the resumed phase distinct alongside their observed cumulative cost. The cumulative total uses the union of request timestamps and preserves unknown counters and pending archives. It never adds an approval's previous generation estimate to ledger observations.

Timings distinguish request wall, local queue wait, upstream TTFT, delivered streaming delta, and explicit client-relative TTFT. Native timing estimates and first-body latency do not supply TTFT for nonstream or unavailable stream framing. Native server task IDs remain separate from proxy sequences. Each epoch includes resource samples once, and each attempt references samples inside its recorded forwarded intervals. Cache-hit counters remain visible with the shared RAM snapshot cache disabled. These are exploratory observations of overlapping slots and phases.

The original CPU placement incident and subsequent repaired epoch have distinct qualification tags. Raw request metrics remain available for interrupted/confounded phases. Model or oracle status does not establish semantic acceptance. To attach an independent acceptance result, specify the unit directory as a key under `reviews` and provide a review receipt path and SHA-256. The receipt must name the candidate patch as `candidate_patch_sha256` and record `decision` as `accepted`, `rejected`, or `pending`. Empty or unbound reviews remain pending or unverified.

Offline validation uses the unchanged v1 metric controls and the multi-epoch controls.

```bash
/usr/bin/python3 -B -m unittest -v test_collect_multi.py
/usr/bin/python3 -B -m unittest discover -s .. -p test_collect_perf.py -v
```
