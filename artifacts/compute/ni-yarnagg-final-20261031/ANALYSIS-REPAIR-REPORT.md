# YARN aggregate power result analysis repair

- Original packet: `/mnt/raid0/llm/tmp/codex-ni-yarn-agg1g-prep-20261031` (read-only).
- New analysis packet: `/mnt/raid0/llm/tmp/codex-ni-yarnagg-final-analysis-repair-20261031`.
- Full prospective plan SHA-256: `dc8fa414b5e50328d294fe6d4b9a32fe5bea97b98a727808c37ceb5c4f4ade68`.
- Original analyzer outcome is preserved: `COMPLETE` binds the FINAL native decision, but `POWER-RESULT.json` was zero bytes and `SUBSET-120-RESULT.json` records `INCOMPLETE` / `AssertionError`.

## Cause and repair

The original subset extractor asserted `real_n == timings.prompt_n`. The native schema defines served `real_n` as `timings.prompt_n + timings.cache_n`; a cached-prefix request splits the served context between prompt and cache tokens. The extractor therefore rejected valid rows (135 per arm) when `cache_n` was nonzero. The repair changes only that assertion to the native equation. All original plan, identity, file-hash, exact-ID, paired-status, native-zone, and scorer checks remain in force.

## Results under the registered rule

Rule: one-sided exact paired McNemar, alpha 0.05, A0-right/A1-wrong is `score >= 1.0` vs `< 1.0`, FAIL iff p <= 0.05. Power target is at least 10 new discordant pairs. NOT-FAIL is not an equivalence or safety claim.

- Fresh full 141: 141 exact pairs; b=7, c=11, p=0.8810577393, mean paired A1-A0=0.0366799645, 18 discordants; NOT-FAIL; declared discordant target reached.
- Prospectively registered original 120: 120 exact pairs; b=5, c=10, p=0.9407653809, mean paired A1-A0=0.0514322917, 15 discordants; NOT-FAIL; declared discordant target reached. Attempted counts: A0=120, A1=120, both=120.
- Historical extension observation b=2/c=1/n=3 is listed separately and excluded from both fresh decisions.

Both fresh outputs were recomputed with the archived `agg_scoring.net_paired_mcnemar` helper; each matches the corresponding native decision artifact. Negative controls reject a missing paired record, a changed prompt hash, and an inconsistent served-token count.

## Integrity and source closure

`SOURCE-ARTIFACTS.sha256.json` records hashes/sizes of the original run and declaration inputs; `SOURCE-IMMUTABILITY.json` records the successful post-analysis comparison. Original failure artifacts are copied as `ORIGINAL-*` and were not overwritten. No inference, model load, launcher, kernel, API, or source-tree write occurred during this repair.

## Duplicate campaign resolution

The pending `yarn-128k-mi210-sol-r11-20261031` cohort is superseded by the completed aggregate run for its original 120-item scientific question. Its source `plan.json` and `items.jsonl` are byte-identical to the aggregate `source-120` files; all ordered item IDs, prompt hashes, non-segment item fields, and 120 prompt blobs match. The A0/A1 server recipe matches after normalizing only ephemeral binary path, port, and slot directory. Model, server, template, runner, cells, and `agg_scoring` hashes match. The r11 watcher has been stopped; do not publish a duplicate READY row or rerun the GPU measurement. See `R11-SUPERSESSION-EQUALITY.json` for hashes and native counts.
