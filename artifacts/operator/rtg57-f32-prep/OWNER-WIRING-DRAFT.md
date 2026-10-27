# Owner-only draft (not applied)

Add to `scripts/vidya/adapters/README.md` source table:

| RTG57 C5 CPU VKQ HYBRID/F32 comparison (`rtg57-c5-vkq-t48`, `rtg57-c5-vkq-t96`; `epyc.rtg57.vkq_comparison.native.v1`) and model-free oracle (`epyc.rtg57.vkq_oracle.native.v1`) | measurement | Prospective timing writer self-hashes per-entry receipt and hashes raw arms, rule, manifest, driver and identities. Adapter re-derives paired relative throughput; n=3, empty protocol, indicative only. T96 is experimental topology-shape. Model-free original oracle is n=1, empty protocol, Judged/Located, original producer script hashes unknown and no model/device applicability. Private synthetic T48/T96 writer-to-planner canaries pass, but installed runtime source/producer and real loop canary must be rebound after merge before claiming wired. | `rtg57_vkq_comparison.py`, `rtg57_vkq_oracle.py`; VB-RTG57-VKQ-WIRE |

Add to `handoffs/active/vidya-belief-substrate-program.md`:

- [ ] **VB-RTG57-VKQ-WIRE — RTG57 native VKQ timing capture and planning context.** Merge and install source branch `codex/rtg57-vkq-wire-20261027`; bind each T48/T96 packet's exact source, producer, protocol and enrollment commit; independently verify the private writer→ingest→planner canary on installed bytes. Capture prospective native timings using the shared ClaimTuple measurement carrier, 3 process pairs, empty protocol and indicative throughput only. T96 is an experimental topology-shape, not registered adoption; preserve original model-free oracle's n=1 and unknown original producer hashes without model/device scope. On first real complete run ingest and prove planner context; no model-quality, speed adoption or GPU claim follows from the oracle. Owner applies index row if required.

Per-entry MAIN-APPROVED.json content, only after MAIN review:

T48: {"id":"rtg57-c5-vkq-t48","source_manifest_sha256":"d9ea735208a9b0d4908e3a6077bf90435e8ece3d5ca3d17c0fa6f853e02d5351","protocol_sha256":"cc6740dedefdef3ace7b9049a349768b5218d108816b4cba045d4a308ffd6536","scope":"experimental-t48-only"}
T96: {"id":"rtg57-c5-vkq-t96","source_manifest_sha256":"c4f0d3a90321885436660e569b4e30de739fd41e393babf6f25a230d9808913a","protocol_sha256":"7f3626128eba7848bc037f929d04e2db4951b6f4bac501e5d76a77518b583499","scope":"experimental-t96-only"}

OWNER-ENROLLED.json in each packet after owner source/task rows are committed and ancestor of origin/main: {"root_commit":"<40-character enrollment commit>","task":"VB-RTG57-VKQ-WIRE"}.
