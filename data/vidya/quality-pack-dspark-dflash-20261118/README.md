# Paired DFlash2 native input packet

Row `handoff-vidya-quality-pack-dspark-dflash-20261118` captures the required `dspark-dflash` profile with Qwen3.8-27B-Q8_0 and its Q8_0 DFlash2 sidecar. DeepSeek V4 Flash 0731 DSpark testing was retired by operator direction. The isolated CPU recipe uses `draft-dflash` and differs from deployed MI210 serving. The full procedure uses 24 CPUs from one allocator-selected quarter, 4096 context, split f16 KV and one slot.

Four distinct raw `/completion` inputs come from the K35 paired request builder. Each proof runs cap 0 and cap 7 for each input on a single v10 server and repeats on a fresh C13 server. Raw completion prompts bypass the registered chat template, whose identity is included for provenance. The finite input census requires eight responses per runtime, effective-cap echoes, zero or absent draft counters at cap 0, positive draft counts and valid accept counts at cap 7, exact request and response bytes, model/runtime/grant custody, in-request PID and library mapping, and cleanup. The result seals the v10 bank before C13 starts.

The four-CPU publisher smoke exercises a real pinned v10 Qwen3-0.6B no-spec completion. It establishes smoke custody only. The pinned CPU feasibility review includes source evidence for both builds and an older experimental native CPU run with the same model and sidecar. CPU DFlash2 capture on the exact v10 and C13 builds needs the full row. The prototype keeps the prior frontdoor JSON mismatch and the broad pack, comparison and planning-context canary open. It conveys no historical DSpark equivalence, quality transfer or promotion authority.

`SOURCE.sha256` verifies the original scratch packet before its launcher runs. Byte envelopes retain the exact source records with their SHA-256 digests. The launcher runs from the pinned scratch path declared in `row.spec.json`.

## Successor

The first full grant ended before launching any server. The keeper's scratch staging changed the inode of the copied CPU feasibility witness. The capture verified its source-path inode even though it only consumes the witness bytes. The successor `handoff-vidya-quality-pack-dspark-dflash-20261118-r2` verifies the staged witness by digest and retains stat checks for external assets and runtime images. Offline checks accepted the exact witness after inode replacement and rejected a byte mutation. An independent native publisher smoke passed on CPUs 116–119 at 01:44:52 UTC. The successor full capture was pending at publication.

The initial specification inherited an unrelated queued architect-general row in its supersession metadata. The scheduler recorded no withdrawal for that queued-only row. The original terminal manifest remains archived as published. The successor has no explicit supersession or lineage overrides. The publisher filed the first attempt as superseded within the DFlash row family and reclaimed zero bytes.

The [successor replay guide](successor/README.md) links the original full rc=1 and the successor readiness PASS. It shows how to decode the archived source envelopes, reconstruct every entry in the published source manifest, and run the saved offline controls in temporary storage.
