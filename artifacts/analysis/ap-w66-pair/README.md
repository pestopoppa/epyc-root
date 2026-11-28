# AP-W66-PAIR runner and receipts

The rank-1 MI210 row `codex-ap-w66-pair-gpu-20261127-r2` completed with exit code 0 at 17:04:58 UTC on 2026-11-27. The direct supervisor, region-lock wrapper, driver, and server all exited. The dedicated endpoint used port 27400 and the recorded physical cores 88–95. The grant also reserved their SMT siblings. The launch confined ROCr helper threads to that affinity. [Rowflow smoke](rowflow-smoke.json) · [Rowflow end](rowflow-ended.txt) · [Process cleanup](cleanup-processes.json)

The first row's setup exposed the scheduler's wider inherited CPU set and a transient vocabulary probe KFD client. A third smoke exposed ROCr helper threads with broad affinity. The successful smoke then qualified C22 save, erase, restore, and streamed reuse. The first direct job inherited the preparation core and exited before launching a server. The successor pins its command explicitly inside the grant and waits for the owned KFD record to retire after the server exits. The private archive preserves the failed attempts and both successful smoke receipts.

The runner verifies C22 binaries and libraries, the model identity, the pinned body and receipt hashes, and live tokenization against the guarded tokenizer receipt. Four split-KV slots each expose 131,072 tokens. Prefix snapshots use the guarded C22 token sequence at the recorded cache depth. Each arm erases the slot, checks the snapshot digest, and restores independently. Both OFF 56 preservation arms use the same treatment, which changes the rendered prompt. Replay peers launch on the first emitted delta from the request that leads, so the receipts preserve historical launch offsets, achieved offsets, and observed overlap.

The result includes two reversed natural blocks for each target, a third natural block for ON 29, and three fixed-length controls. Rows carry streamed TTFT, native prefill and decode, MTP counters, timing joins to server logs, and resource samples during peer overlap. The accepted-turn rates divide substantively accepted immediate replay turns by summed target-request wall seconds. The quality receipt records strict-format compliance for all six OFF 56 summaries. Generated tool proposals stayed inert. [Numeric summary](summary.json) · [Quality judgments](../ap-w66-pair-quality/README.md)

## Reproduce the numeric summary

The private archive includes the submitted source, sealed input metadata, wire bodies, raw streams, server log, resource samples, cached slot files, and scheduler receipts. The model remains in the registered model store. [Private archive manifest](archive-manifest.json)

```sh
python3 -B artifacts/analysis/ap-w66-pair/summarize.py \
  /mnt/raid0/llm/archive/compute-evidence/ap-w66-pair-20261127-r2/r2/out/run \
  /tmp/ap-w66-pair-summary.json \
  --quality-dir artifacts/analysis/ap-w66-pair-quality
cmp artifacts/analysis/ap-w66-pair/summary.json /tmp/ap-w66-pair-summary.json
```

For a fresh measurement, publish a successor of the included row spec from a private scratch directory. Carry over the sealed `prefixes.json` and verified runner source from the archive. Assign a new row ID, allocated port and output path. The row must hold the MI210 and the recorded host CPUs before starting the runner. [Rowflow spec](spec.json) · [Launcher](launch.sh) · [Runner](run.py)
