# CPU-FA-VKQ-2 exact C5 comparison

The target run completed rc0 on 2026-11-03, with 20 distinct fresh CPU processes: five HYBRID and five legacy launches at each depth, alternating order. All native outputs identify C5 c72ec82f5, 48 threads, F16 K/V and 32 generated tokens. The captured per-launch plans use the same prepared binary/model products, default HYBRID versus GGML_FA_VKQ_F16=1; the GGML_FA_VKQ_F32 override is absent. Each process has at least two during-run own-library witnesses. The retained job drains and verifies each own process group before writing its record. This is the full target mode, not qualification.

| Depth | HYBRID median tok/s | Legacy median tok/s | Effect (higher better) | Observed floor | Result |
|---|---:|---:|---:|---:|---|
| 16,384 | 19.917212 | 19.557956 | +1.836879% | 36.392217% | within floor |
| 65,536 | 13.137735 | 12.866371 | +2.109095% | 4.110452% | within floor |

The floor is max(2%, HYBRID range/median%, legacy range/median%). The large 16k range is retained rather than omitted. This satisfies the task's record-decode-delta-with-noise-floor done-when. It does not establish superiority or non-regression, and carries no production, promotion, MTP or quality conclusion. The existing VB-CPU-FA-VKQ2-WRITE projection/planning canary remains separate.

Native per-launch files are losslessly gzip-compressed with original and stored SHA-256s in SHA256SUMS.json. prepared.json binds the three model shards and kernel products; validation.json records the source-independent result checks and recomputation. verdict-proposed.json is for owning-session review; this subagent did not file, tick, or commit.

The owning session reviewed and filed the preserved proposed verdict through `file_result.py`; checkbox application is part of the owning wrap-up.
