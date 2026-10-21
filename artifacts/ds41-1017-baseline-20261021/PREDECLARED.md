# DS41-1017 target-only baseline: predeclared design (written 2026-10-21 before any run)

Instrument: `matched_process_v2` (AK loop `serving.py`), driver `gate_1017.py` (sha256 recorded in `APPROVED` when main approves).
Recipe: `ds41-1017-mxfp4-cpu-t48-targetonly` (template_hash 65f1c793..., request_digest e50732d9..., 1 frozen request, n_predict 256, greedy).
Model: 1017 MXFP4-experts 9-shard split, digest ba9f129c... (per-shard sha256 from `download_1017.log`, not recomputed).

Predeclared counts and comparisons (fixed now, not adjustable after seeing any sample):
1. **Floor:** N_AA = 24 independent A/A pairs (48 launches) on the CHAMPION build `cpu-20261020-dd3d9721c`, random per-pair order (seed drawn and retained by the instrument). The floor is the instrument's own bar for N_CMP = 5 comparison pairs, `unit = process`. This is the first DS41-1017 process-level floor; it is not comparable to the Sept Q4+DSpark 3.412% / 4.533% floors (different model, no speculation).
2. **Comparison:** N_CMP = 5 alternating pairs (10 launches), champion `dd3d9721c` (anchor) vs candidate C `f0c96dc1f`, same recipe, same requests, same host state. Effect = median(C)/median(champion) - 1 (process unit). The verdict is the instrument's `decisive` flag: a delta inside the floor is "not decisive", never a pass or fail. A sign claim is reported alongside (sign of the effect and the number of pairs in which C > champion).
3. No `--apply`, no write to any campaign store, no champion-of-record change. The floor row is written only under `aa/floor-store/` in this directory.
4. Invalid arms: the instrument's own single same-tail reschedule applies; any further failure aborts the run and the partial `launches-*.jsonl` is kept as an informal dispersion check only.
5. The comparison does not depend on speculation: if either build fails to load/serve the MXFP4 split file, the run stops and records the failure; nothing is retried on another recipe.
