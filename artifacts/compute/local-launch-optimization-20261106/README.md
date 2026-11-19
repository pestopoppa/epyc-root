# Local launch optimization — 2026-11-06

## Question

What launch layout actually maximizes local serving throughput for the two
champion-candidate C6 servers on this host?

- **CPU:** Qwen3.8-Flash-Next UD-IQ4_XS + shared MTP Q8_0, 0-95
- **GPU:** Qwen3.8-27B Q8_0 + DFlash2 Q8_0, MI210 (ROCm0)

The previous manual launches used:

- CPU `-np 4 -c 262144 -t 48 -tb 48`, f16 KV, `--no-kv-unified`, MTP d4
- GPU `-np 4 -c 262144 -t 8`, f16 KV, `--no-kv-unified`, DFlash2 n8

The live CPU request was 57k tokens and decoded at ~12.5 tok/s; the GPU 50k
requests decoded at ~29-31 tok/s. The canonical short-context references are
~50 tok/s (CPU 8k, 102-token prompt, np1) and ~76-80 tok/s (GPU np1, 16k,
f16, DFlash2 n8, acceptance 0.73). The 41.6/40.4/36.9/32.1 GPU curve is the
production np4 / 393k / q8_0-KV / n7 shape, acceptance 0.37-0.39.

## Method

- One server at a time, under `region-lock`:
  - CPU: `--cpu-list 0-95 --gpu-quiet shared --role bench`
  - GPU: `--gpu-quiet exclusive --role bench-gpu`
- Fixed prompt from `prompts/` (wikitext2 slice), `/completion`, greedy,
  `cache_prompt=false` for the first measurement and `true` for the repeat.
- Record `timings.prompt_n`, `timings.predicted_n`,
  `timings.predicted_per_second`, draft acceptance, `/proc/PID/status`,
  per-thread CPU masks, `numastat -p`, and `rocm-smi` for GPU arms.
- CPU long arms evict page cache (`evict_nodes_force.sh 58`) before launch so
  `numactl --interleave=all` placement is not distorted by page-cache pressure.
- Screening context is 32k tokens for CPU (prefill cost) and 50k for GPU.
  Confirmation is 50k for CPU.

## Files

- `harness.py` — one-arm launcher/measurement/cleanup.
- `make_matrix.py` — generates `matrix.json` (22 arms).
- `analyze.py` — ranks `summary.json` into `ANALYSIS.md`.
- `runs/<arm>/result.json`, `server.log`, `evict.log` — raw evidence.
- `summary.json`, `SUMMARY.md`, `ANALYSIS.md` — rollups.

## Results

See `ANALYSIS.md` (generated after the matrix completes).

## Caveats

- This is an exploratory optimization, not a formal measurement claim.
- The IQK-FA store is `cpu-20261031-729599d69-c6-iqkfa-on` (10500), not the
  champion `cpu-20261105-65da39eb1-c6fold2` (10512). It lacks the C6 Q8_0
  prefill fold and V11-102 is PEND; it is an A/B candidate only.
- KV q8_0 arms are a speed/quality trade; the canonical recipe keeps f16.
- The GPU production-shape arm uses q8_0 KV / n_max 7 / unified KV; it is a
  different quality/serving shape from the canonical np1/16k/f16/n8 reference.
