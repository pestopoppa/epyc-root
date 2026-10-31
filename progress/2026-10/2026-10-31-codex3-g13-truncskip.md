# G13 full native diagnostic — 2026-10-31

`codex-ni-kbrag-g13-truncskip-r2-20261030` completed rc0: fixed 70 certification truths across six newly embedded arms plus a separately scored canonical index, 490 native case records. Recall@10 is higher better; deltas compare each private arm with the newly re-embedded 4000-character / 256-token / plain baseline, not the canonical stored arm.

| Arm | Recall@10 | Matched delta |
|---|---:|---:|
| 4000 / 256 / plain | 0.367857 | 0.000000 |
| 4000 / 256 / punctuation | 0.375000 | +0.007143 |
| 4000 / 300 / plain | 0.340476 | -0.027381 |
| 4000 / 300 / punctuation | 0.327381 | -0.040476 |
| 1100 / 256 / plain | 0.364286 | -0.003571 |
| 1100 / 256 / punctuation | 0.353571 | -0.014286 |

All six arms are below the strict +0.02 descriptive trigger; separately the canonical stored index is 0.367857. This does not assess the original historical 0.5690 gate, whose 577-file / 18,010-chunk corpus differs from this 1,522-file / 34,214-chunk current index. No adoption or K7 quality closure follows.

Independently re-derived every case against all 70 frozen IDs/evidence lists and ranked top ten, matching all seven native means; validated all 1,522 source snapshot hashes and pinned catalog SHA, and independently matched 1,520 chunk multisets to catalog; two declared current snapshots remain changed. This is indexed-text equivalence, not historical whole-file identity. Eight real worker receipts match source/invocation/exit and aggregate 105,950 new encodes, 23,845 existence skips and 0 cache loads; parent-local counts remain separate. Query masking was unchanged, exact encoded punctuation IDs were masked on document rows only. Original case and stale/missing evidence denominators remain unchanged. [belief: cc]

[Original records and independent checks](../../artifacts/compute/codex3-g13-truncskip-20261031/SHA256SUMS).
