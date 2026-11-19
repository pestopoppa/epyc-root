# KPF-18 SeedControl failure cleanup

The source-bound patch fixes two paths in the retained disabled group-3 transport:
failed capture no longer falls through into native-release polling, and response
cleanup failure cannot skip connection closure or mask the original typed STOP.
It records the failed capture and any secondary cleanup error, then refuses.
A successful capture still needs the existing task-bound native release witness.
No failed capture publishes the normal attempt row.

Eight full-consumer model-free tests passed on 2026-11-19. They import the entire
patched module and run `SeedControl.__call__`, its real SSE capture, socket
watchdog, native parser and receipt code. HTTP responses, slot observations and
native log lines are synthetic. A real owned socketpair and watchdog exercise
connection closure and thread joining. Cases cover success, reordered native
release evidence, connect/header failure, malformed SSE, STOP, response-close
failure and STOP concurrent with response-close failure. The last case initially
exposed exception masking inside `capture`'s finally; cleanup now retains its
secondary exception without throwing across that boundary.

Run from any checkout with the retained inputs available:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -B -m unittest discover \
  -s docs/reports/kv-cache/kpf18-seed-cleanup-20261119 -p test_consumer.py -v
```

`source.json` pins the existing transport, six imported dependencies, patch and
patched output by SHA-256. The test applies the patch in a temporary directory
under `/mnt/raid0/llm/tmp/kvu/seed-cleanup-20261119`, then removes that directory.
It never changes the predecessor. A generated patched transport is also retained
at that scratch root; it is not the sealed runtime candidate.

This is a tested software patch, not full successor integration or GPU
qualification. Outer/inner runtime barriers and predecessor inventories remain
unchanged. Actual native cancellation/release, bounded slots transport, owned
server/descendant cleanup and current GPU admission remain separate requirements.
No model was loaded, no row published and no historical layout verdict changed.
GitNexus status/impact found no indexed repository: graph risk is unknown.
