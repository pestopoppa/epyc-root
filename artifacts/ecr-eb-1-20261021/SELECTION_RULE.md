# ECR-EB-1 selection rule (predeclared; committed BEFORE any ranking is computed)

Authored 2026-10-21 by lane dpf-sample-yarn-zc. At commit time no ranking, headroom or SD filter had been computed or viewed; only
schema facts (language values, internet flag counts, the three GPU-string hits in task shards, which are all "CPU only"/"No GPU" negations) were read.

## Inputs (all local, zero compute, no image pull)
- Card: `README.md` of HF `ByteDance-Seed/EdgeBench` @ `6cc5a7f1b3288ce52484ad828177b8cc86b05b75`, section "Per-Task Scores by Time Budget (51 tasks)" -> per task and model the six values @2h/@4h/@6h/@8h/@10h/@12h (copy at `/mnt/raid0/llm/tmp/dive-dpf-1361/README.md`).
- `tasks.jsonl` (same sha, 51 rows): `language`, `internet`.
- Task shards `<task>.json` (same sha; copies at `/mnt/raid0/llm/tmp/dive-dpfw2-edgebench-shards/shards/`): CPU-only check.
- Paper arXiv 2607.05155 HTML, sha256 prefix `037e38aa` (`/mnt/raid0/llm/tmp/dive-dpf-1361/paper.html`), appendix G.6 tables A7.T8-A7.T13: per task and model `mean ± sd` (sample SD of run scores rescaled to 0-100, >=2 valid runs; `*` marks cells with <3 runs).

## Join
Join on task name (`task_id`) across card, tasks.jsonl, shards and paper tables. Rows missing from any source are DROPPED and counted (not imputed).

## Filters (applied in this order; each stage count is reported)
1. Language in {Python, C++} (exact strings of `tasks.jsonl`).
2. `internet == false`.
3. CPU-only: the shard JSON text contains no positive GPU requirement. Positive requirement regex (case-insensitive): `(requires?|needs?|must use|use an?|uses?)\s+(an?\s+)?(nvidia\s+)?(gpu|cuda)\b`. Negations ("CPU only", "No GPU", "CUDA is disabled") are not requirements. A missing shard fails this stage (drop, counted).
4. Non-saturated at 2 h: the maximum over the five models of the @2h score is < 90.0 (0-100 scale). Models with `—` at 2 h are ignored for the max.
5. Positive 2 h -> 12 h headroom: let H = mean over models having BOTH @2h and @12h of (score@12h - score@2h); require at least 3 such models and H > 0.
6. SD exclusion (fixed before ranking): exclude the task if the 12 h run-to-run SD of GLM-5.1 OR DS-V4-Pro (paper cell) is > 15.0 points on the 0-100 scale. A missing SD (cell with <2 valid runs, or no paper row) does NOT exclude; it is flagged `sd_missing` in the CSV. Caveat stated up front: the paper reports SD only for the final (12 h) score, not at 2 h.

## Ranking and cut
Rank survivors by H descending; ties by `task_id` ascending. Keep the top 8 (fewer if fewer survive). The slice budget is 2 h per task, CPU-only.

## Scope limits
Scores are as published on the card (rescaled 0-100 by the benchmark; higher is better for every task after rescale, as the card states a rescale for all). No local inference was run, no image was pulled, nothing in a shard was executed.
