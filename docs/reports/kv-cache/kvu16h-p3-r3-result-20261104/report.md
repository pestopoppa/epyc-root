# P3: unified-KV decode cost vs occupied pool (MI210, v10 ffc1bac82, Qwen3.8-27B Q8_0 + DFlash2)

## A1 parked neighbours (resident, idle; --no-cache-idle-slots), status ok

P = 57084 tok on slot 0; park mode prefill; pool 393216 cells.

| level | resident max (frac pool) | drafted tok/s | Δ vs base | acc | no-draft tok/s | Δ vs base | decode-only |
|---|---|---|---|---|---|---|---|
| L0_base | 57594 (0.146) | 35.511 | -0.1% | 0.372 | 22.173 | +0.0% | True |
| L1_156k | 156957 (0.399) | 24.764 | -30.4% | 0.372 | 14.538 | -34.4% | True |
| L2_258k | 258517 (0.657) | 18.877 | -46.9% | 0.372 | 10.816 | -51.2% | True |
| L3_358k | 358833 (0.913) | 14.935 | -58.0% | 0.372 | 8.582 | -61.3% | True |
| L0_after | 57590 (0.146) | 35.609 | +0.1% | 0.372 | 22.172 | +0.0% | True |

- Baseline (mean L0_base, L0_after): drafted 35.56, no-draft 22.172 tok/s; ABA drift (no-draft) -0.0%.
- **Decode loss at the >=300k fill (L3)**: no-draft 61.29%, drafted 58.0%.
- Peak resident KV tokens 358838 / 393216 = 0.913 (from /slots, sampled during decodes).
- Server log counts: {'failed to find a memory slot': 0, 'context size has been exceeded': 0, 'failed to find free space in the KV cache': 0, 'exceeds the available context size': 0, 'purging slot': 0, 'Unable to restore slot': 0, 'saving_idle_slot_lines': 0}
- VRAM peak 51.71 GiB device, own pid 51.7 GiB.

**Verdict (no-draft isolates attention): P5 trigger (>=5%): MET; split-per-slot trigger (>=15% at >=300k): MET.**
