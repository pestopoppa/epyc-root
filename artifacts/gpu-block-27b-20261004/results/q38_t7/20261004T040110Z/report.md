# Q38-T7 — DFlash2 at the production shape (2026-10-04T04:05:37Z)

Server: b10303-ffc1bac82 · speculative ['none,draft-dflash'] · slot n_ctx 262144 · argv n-max-7 True · SLOTS_DEBUG env None

**Correctness: PASS** — speed numbers VALID.

Degeneracy detector: `inf70-degeneracy.v2` (loops / stuck tokens / garbage only; semantic content unchecked). Correctness = paired drafted-vs-no-draft identity, ground-truth answers, needle.

## B — decode vs context (probe_decode method; MTP comparator = 2026-10-01 probe at the pre-KVU-16 shape)

| target | prompt tok | variant | rep | prefill tok/s | TTFT s | decode tok/s | gen | draft acc | degeneracy / needle | busy before |
|---|---|---|---|---|---|---|---|---|---|---|
| ~2k | 2543 (cache 0) | drafted | 1 | 410.1 | 7.676 | 31.89 | 1500 | 0.3091 | OK | - |
| ~2k | 4 (cache 2539) | no-draft (n_max 0, cached) | 1 | 34.9 | 0.135 | 30.47 | 1500 | None | - | - |
| ~2k | 2388 (cache 154) | needle | - | 459.4 | None | 82.21 | 17 | 1.0 | correct | - |
| ~2k | 4 (cache 2538) | needle (no-draft) | - | 10.6 | None | 30.01 | 17 | None | correct | - |
| ~16k | 15971 (cache 0) | drafted | 1 | 554.4 | 30.875 | 41.13 | 1500 | 0.3534 | OK | - |
| ~16k | 4 (cache 15967) | no-draft (n_max 0, cached) | 1 | 7.4 | 0.592 | 25.91 | 1500 | None | - | - |
| ~16k | 15816 (cache 154) | needle | - | 595.7 | None | 31.35 | 18 | 0.2857 | correct | - |
| ~16k | 4 (cache 15966) | needle (no-draft) | - | 40.5 | None | 28.48 | 18 | None | correct | - |

| target | DFlash2 drafted tok/s | MTP drafted tok/s | ratio | DFlash2 acc | MTP acc | no-draft (this run) |
|---|---|---|---|---|---|---|
| ~2k | 31.89 | 36.82 | 0.87 | 0.31 | 0.43 | 30.47 |
| ~16k | 41.13 | 40.81 | 1.01 | 0.35 | 0.59 | 25.91 |

VRAM: {'n_samples': 267, 'interval_s': 1.0, 'pid': 1703677, 'kfd_peak_gib': 59.773, 'kfd_min_gib': 58.879, 'card_peak_gib': 59.852}
Server log window: bytes 27542756–27559320 of /mnt/raid0/llm/epyc-orchestrator/logs/llama-server-8083.log (B4g reuses this window); bad lines {'failed to find a memory slot': 0, 'Context size has been exceeded': 0}.
