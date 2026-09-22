# GLM-5.3 AutoKernel evidence (preserved 2026-09-22)

GLM-5.3-Flash was retired on 2026-09-22 (operator). Its AutoKernel scratch under
`/mnt/raid0/llm/tmp/aku-glm53-*` and `aku12a-glm53-*` (113.6 GB) was deleted with operator
confirmation. This directory keeps what handoffs and progress notes cite:

- `files/`: every cited file or directory under 1 MB, copied verbatim; the path mirrors
  `/mnt/raid0/llm/tmp/`. `MANIFEST.json` maps each original path to its archived copy, with its
  SHA-256.
- `five-loop-store-experiments.nopayload.jsonl.gz`: all 313 rows of the five-loop store's
  `experiments` table. Every column is kept except `payload` (5.5 GB), which is replaced by
  `payload_bytes` and `payload_sha256`.

Not preserved: the cited run directories themselves (0.1–6 GB each), `cpu-profiles` (46 GB) and the
full `experiments.db`. Citations to those paths are now dead by design.

Kernel code survives in git, not here:
- keeps: fork branches `ak/glm53-recovered-accumulator-20260912` and
  `experimental/glm53-keeps-on-v10-20260922`;
- unmeasured in-flight diffs: `../glm53-inflight-candidates-20260922/`.
