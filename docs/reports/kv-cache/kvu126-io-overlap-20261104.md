# KVU-12.6 model-hash I/O overlap — 2026-11-04

The session reports one SHA-256 read of `/mnt/raid0/llm/models/Qwen3.6-35B-A3B-MTP-Q8_0.gguf`, **37,801,097,504 bytes**, from **14:17:48 to 14:19:11 UTC**. The preparer reported these approximate endpoints and byte count; this audit did not independently capture the read or its process.

A single pass over the retained `grants/*.ended` files found four row-runner intervals overlapping that read. The copied end records and SHA-256 locators are in [`kvu126-io-overlap-20261104/`](kvu126-io-overlap-20261104/). Every listed row ended `rc=75 reason=disk-floor`. The timestamps show overlapping **runner intervals**, not proof that a target inference, build, or index actually executed.

| Row | Recorded runner interval (UTC) | Owner | Result |
|---|---|---|---|
| `ufh12-gs-frozen-gnx-20261104` | 14:17:50–14:17:51 | `handoff-agentic-serving-harness-fixes` | disk-floor, rc75 |
| `cafe2-v10-verify-cost-build-20261104` | 14:17:57–14:18:04 | `h-speculative-decoding-mtp` | disk-floor, rc75 |
| `kvu-kpf174-custody-r1-20261104` | 14:17:58–14:18:05 | `h-kvu` | disk-floor, rc75 |
| `ufh14-repl-emb23a-parse-v2-20261104` | 14:17:59–14:18:07 | `handoff-agentic-serving-harness-fixes` | disk-floor, rc75 |

A fifth end record, `handoff-kvu19-p5-champion-a1-20261104`, ended at **14:17:49 UTC**, one second after the reported read began, with `rc75 disk-floor`. It has no start timestamp or owner in that end record, so its interval and any overlap in target execution are **unknown**. Its retained filing-due record names owner `handoff-kvu`; that is ownership metadata, not a residency or process-activity observation. The retained [keeper excerpt](kvu126-io-overlap-20261104/p5-keeper-excerpt.txt) shows launcher PID 1519164 armed and granted at 14:17:46Z; this proves a launcher/grant event, not native inference. GPU/VRAM snapshots were zero at 14:17:46Z and 14:17:55Z, both outside the one-second overlap, so they cannot prove the device was idle during that overlap. The scratch tree contains only the earlier qualification logs and no identified official A1 run directory/result at audit time; absence is not proof that no payload started.

The UFH14 scratch tree also contains a `phase=run` launch record for frontdoor PID 1526438 naming the **same 35B model**, and its server log records model loading. The launch record filesystem mtime is 14:18:00.937576Z, inside the hash interval. The record contains no absolute process-start timestamp, and the producer bytes were not independently sealed to this row; the mtime is a temporal clue, not conclusive proof of simultaneous model I/O or an inference window. [Bounded native record and timestamps](kvu126-io-overlap-20261104/ufh14-file-observations.json) are preserved.

The GS-index and CAFE-2 filed verdicts independently report their official result absent; the available end records alone do not prove whether any work inside the other runners began. A file read consumes I/O bandwidth; these records do **not** establish it caused a disk-floor stop. Runs without retained start/end pairs, other sessions, and unrecorded host processes remain **unknown**, not clear. No conclusion about benchmark validity, I/O contention, throughput, or absence of other work follows from this bounded audit.
