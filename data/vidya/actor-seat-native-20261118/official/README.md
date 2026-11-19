# Official AutoKernel actor-seat native capture

The source-custody verdict for `vb-ak-seat-native-instrument-20261118` is
**PASS**. The official allocation covered 24 CPU IDs, 72–95. The allocator
started the job at 16:03:29 UTC and completed it with rc=0 at 16:03:44 UTC
on 2026-11-18. The capture result records `status=complete` and confirms
owned actor cleanup, owned server cleanup and a free port.
[Allocator end](allocator.ended) · [Allocator completion](allocator.complete) ·
[Pinned manifest](manifest.json) · [Capture result](RESULT.json) ·
[Filed verdict](verdict.json). The public capture result labels the filesystem
stat fields. The archive member `RESULT.original.json` retains the original
result bytes and SHA-256 used by the filed verdict.

The [original archive](native-official.tar.gz) retains call-time `/props`
for `vidya-seat` on the v10 CPU build `b10303-ffc1bac82`, with per-slot
`n_ctx=8192`. It also retains the exact prompt, offered variable-context
bundle, original OpenCode export and the call and metrics records joined by
`d3373069549c424eb7830db933cae11e`. The bundle captures what the producer
offered. The metrics record zero bundle tool calls, so actual section reading
is unverified.

The task response was schema-invalid and repair ran, as recorded by
`schema_valid=false` and `repair_ran=true`. The source verdict covers
custody of this one call. The timing observation describes a single run, and
the canonical research adoption and campaign acceptance remain open under
`VB-AK-SEAT-FINISH` in the
[belief-substrate program](../../../../handoffs/active/vidya-belief-substrate-program.md).

Offline replay of the archived bytes yielded one `Judged/Located`
observation, `clm_akseat_0eb4164743049e618025886f`, with three frames,
zero refusals, zero ledger writes and zero new inference calls. The
[archive binding](ARCHIVE.json) lists original packet checksums. The
[replay receipt](replay-receipt.json) records the verified packet and
archive member SHA-256 digests, raw call and metrics line digests, and the
three frames with an archive-relative source locator.

To repeat the replay from the repository root, extract the archive into a
fresh scratch directory and pass that directory to the existing adapter.

```bash
packet=data/vidya/actor-seat-native-20261118/official
scratch=$(mktemp -d /mnt/raid0/llm/tmp/vidya-belief-substrate/seat-replay.XXXXXX)
tar -xzf "$packet/native-official.tar.gz" -C "$scratch"
PYTHONPATH="$PWD/scripts/vidya" python3 - "$scratch" <<'PY'
import os
import sys

from adapters import autokernel_actor_seat as adapter
from claim_tuple import grade

os.chdir(sys.argv[1])
log = "actor-replies/actor-calls.jsonl"
(row,) = adapter.native_rows(log)
assert grade(adapter.project(row))[:2] == ("Judged", "Located")
assert len(adapter.frames_for_path(log, as_of="2026-11-18T16:11:50+00:00")) == 3
PY
```

The [scratch cleanup record](../../scratch-cleanup-20261118.json) records
181,948,416 allocated bytes reclaimed in this turn (173.5 MiB). The four current
EXP01 model arms and active parity input remain pinned; unique native failure
and merge-recovery evidence remains preserved.
