# DCP-9a Claude Code cache-read trajectory — 2026-11-17

The retained EPYC vault snapshot shows higher cache-read fractions at the end of 166 of 182
sessions with comparable first and last buckets. The original 61-transcript cohort and the task
quality inputs required by Definition 1 are missing. DCP-9a remains open.

## Input identity and coverage

The read-only scan covered the 227 top-level JSONL files in
`/mnt/raid0/llm/cloud-llm-vault/epyc/claude/-workspace`. It read 729,797,029 bytes and 309,143
lines. The [aggregate artifact](vault-trajectories.json) lists a SHA-256 for each source file and
binds the sorted digest multiset, one newline-terminated digest per file, to
`5b937d9aefba4b123a5c80c7d36b0920a5fd4b0f8479b1106340a913ac6c02ed`.
The artifact SHA-256 is `baf840d0f09af532a09cc68e9097d1751d342adffed9dceb17e474f199ebab0e`.
One digest occurs twice across two files with zero assistant usage records. All 101,022 assistant
usage rows had four valid counters and message IDs. The 54,584 repeated-ID rows were counted in the
raw-row sensitivity and collapsed to the last usage row per message ID within each file for the
primary estimate. All 46,438 retained messages had valid timestamps. There were zero malformed
JSON or non-object rows. Forty-one files contributed no timed messages and two of 1,773 buckets
had zero input tokens, leaving `h` undefined. The export contains token aggregates, elapsed times,
and file digests. The extraction scope covers top-level journals only and gives no completeness
guarantee for provider activity outside those files.

```bash
PYTHONDONTWRITEBYTECODE=1 python3 scripts/dev_harness/dcp9a_cache_trajectory.py \
  /mnt/raid0/llm/cloud-llm-vault/epyc/claude/-workspace \
  --expect-files 227 --max-bytes 730000000
```

## Eq. 4 trajectory

Within each file, sort deduplicated messages by UTC timestamp and break ties by journal line
order. Divide that sequence into up to ten nearly equal message-count buckets. The export gives
bucket bounds in elapsed seconds, measured from the first retained message, together with the
numerator and denominator components for `h`. Counts and fractions describe the finite retained
snapshot. The analysis stopped after one bounded scan of that snapshot.

| Cohort | Observations | Cache-read `h` | Cache-creation share | Uncached-input share | Input:output |
|---|---:|---:|---:|---:|---:|
| September 7 point estimate, original 61 transcripts | 45,902 usage rows | 0.9845384 | 0.0154405 | 0.0000211 | 350.5:1 |
| Vault snapshot, raw rows | 101,022 usage rows | 0.9767581 | 0.0230832 | 0.0001587 | 213.3:1 |
| Vault snapshot, primary deduplicated estimate | 46,438 messages | 0.9847079 | 0.0151915 | 0.0001006 | 369.0:1 |

The median first- and last-bucket `h` values across the 182 comparable sessions were 0.8750
and 0.9928. The median within-session increase was 11.19 percentage points. The other 16
comparable sessions declined. Across 186 sessions with defined `h`, median session intensity
was 18,517,351 reported input-plus-output tokens. Bucket widths vary with session activity and
the short sessions have fewer buckets. The counts describe retained-session behavior.

## Historical cohort and Definition 1

The September 7 point estimate used `/home/node/.claude/projects/-workspace/*.jsonl` as it
existed at calculation time. The dive digest reports the sums and states that the read-only
calculation wrote no files. The live directory now has 17 files and no assistant usage rows
through September 7. The retained vault has 152 files with 66,660 usage rows through that
date, so a timestamp cutoff gives a different cohort. Recovering the historical trajectory
requires the original 61-file snapshot or a manifest identifying those files and their exact
read extents in retained copies. [September 7 dive digest](../../../research/deep-dives/intake-digests/2026-09-07-ids-1313-1345.md#intake-1333record--the-harness-effect-how-orchestration-design-sets-the-token-economics-of-enterprise-agentic-ai)

Definition 1 requires comparable completed-task token intensity `τ` and quality `Q` across
successive releases, with `Q` scored under a fixed judge protocol. Its conditions are increasing
`τ` and `ΔQ/Δτ < Q/τ`. The journals supply session counters and timestamps. The missing join
is release → comparable completed task → total task tokens and fixed-judge quality score.
The Definition 1 verdict is recorded as `null`. [The Harness Effect, §3.2](https://arxiv.org/html/2607.06906v1#S3.SS2)
