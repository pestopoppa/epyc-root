# A3B thinking mode evidence audit

The real-task pilot does not establish a quality benefit from thinking. It used different tasks and devices across modes, and the mixed-mode NARIQ case changed both the packet and the output cap. In the earlier CPU canary, ON and OFF each had 3/5 sound results. ON generated 40,322 tokens vs OFF 27,207 (+48.2%) on 96 and 97 worker calls, respectively. Median task wall was 692 s ON vs 503 s OFF. The arms used different output caps and wall budgets, so these figures describe the tested settings.

## Real-task pilot token accounting

| Native request group | Complete / recorded | Prompt | Cached | Uncached | Generated |
|---|---:|---:|---:|---:|---:|
| GPU thinking workers | 179/179 | 5,769,706 | 5,415,572 | 354,134 | **91,108** |
| CPU nonthinking workers | 64/64 | 1,548,231 | 1,446,484 | 101,747 | 29,512 |
| Nonthinking reviewers | 8/8 | 33,440 | 309 | 33,131 | 407 |
| Separate thinking wire control | 1/1 | 254 | 0 | 254 | 32 |

Generated counts include reasoning, response, and tool-call output. Native usage reports no reasoning-only token count. All 252 records have complete native counters. For the wire control, native timing counters are available without an API usage object. Prompt totals include cached prompt tokens and sum over requests. A resume can prefill history again, which counts as new compute. Mirrored per-unit logs and OpenCode event copies are excluded.

| Logical task | Worker mode | Complete / recorded | Prompt | Cached | Uncached | Generated |
|---|---|---:|---:|---:|---:|---:|
| PAW-5 | ON | 33/33 | 518,515 | 440,640 | 77,875 | 14,389 |
| DS41-W-66 | ON | 60/60 | 1,722,703 | 1,618,634 | 104,069 | 21,212 |
| DS41-W-75 | ON | 15/15 | 214,813 | 201,228 | 13,585 | 3,862 |
| UTM-B2-VERBATIM-WITH-COMPACTION | ON | 41/41 | 1,644,360 | 1,539,573 | 104,787 | 24,052 |
| NARIQ-LIBTRELLIS-MAP-1 | ON | 30/30 | 1,669,315 | 1,615,497 | 53,818 | 27,593 |
| NARIQ-LIBTRELLIS-MAP-1 | OFF | 35/35 | 1,222,239 | 1,146,233 | 76,006 | 19,540 |
| PFXC-A3 | OFF | 29/29 | 325,992 | 300,251 | 25,741 | 9,972 |

The 91,108 thinking-worker generated tokens include 39,758 from the three source-correction attempts, 23,853 from PAW and W66 interrupted, retried or resumed segments, and 27,497 from the other original attempts. PAW's first scheduling attempt issued zero requests. Its next attempt generated 2,255 tokens upstream with zero output delivered under the transport defect. W66's original no-edit outcome also encountered misleading shell-denial guidance. The [attempt table](pilot-attempts.tsv) identifies the cap failure and other audit dispositions. The [logical-task table](pilot-logical-tasks.tsv) includes reviewer rows.

## Prior paired canary evidence

The completed C22 canary's original independent audit accepted ON 4/8 and OFF 2/8, with two stale skips in each mode. The apparent ON wins come from R LOOP-62, where OFF faced packet ambiguity in a retained GPU np1 run and ON ran in GPU np4, and F NOFOLD-1, where OFF ran on CPU and had a false-verifying destructive patch while ON ran on GPU. F LOOP-62 and R NOFOLD-1 pass both modes across different serving conditions. MM-5 passes neither original mode, and one CPU OFF attempt was contention-affected. [Independent outcomes](/mnt/raid0/llm/tmp/taskflow-finish-20261126/FINAL-VERDICT.json) · [Attempt and device join](/mnt/raid0/llm/tmp/taskflow-finish-20261126/MATRIX.json)

| Same-task GPU pair within a canary configuration | Hand-audited OFF / ON | OFF generated | ON generated |
|---|---|---:|---:|
| Original TU-GR-1, R retained np1 | Fail / Fail | 10,501 | 7,230 |
| Original TU-GR-1, F retained np1 | Fail / Fail | 5,778 | 7,938 |
| Corrected TU-GR-1, F np4 | Fail / Fail | 5,018 | 8,005 |
| Corrected MM-5, F np4 | Fail / Fail | 7,687 | 14,715 |

Corrected pairs use their matching revised packet and trusted acceptance. They are separate from original pairs. The ON and OFF profiles used different output caps. The direction of the generated-token difference varies in the retained TU-GR-1 comparisons. None of these same-task GPU pairs has an ON-only success. The r8g CPU pairs pass LOOP-62, NOFOLD-1 and MM-5 in both modes. TU-GR-1's ON result was false-rejected by the reviewer and WS4's OFF result was blocked by the line-range pathspec defect. These outcomes leave uncertainty about conditional benefits. [C22 canary counts](c22-canary-attempts.tsv) · [r8g canary counts](r8g-canary-attempts.tsv) · [r8g hand audit](/mnt/raid0/llm/tmp/ws58-a3b-finish-20261126/docs/design/taskflow-stage1-canary-findings.md:286)

## Useful matched reruns beyond W66 and PAW

- **NARIQ first.** The original OFF attempt hit the 2,048-token cap. The recovered OFF draft and targeted ON correction both had material engineering defects. A fresh pair can hold the exact source bundle, complete brief, GPU, wall and output ceilings, and independent semantic review constant.
- **UTM second.** The original ON worker bypassed the behavior the test needed to exercise. The targeted ON correction produced the accepted test. An identical behavior-complete brief and independent mutation controls in both modes would answer whether thinking helps accomplish the same scoped test.
- **PFXC optional.** Both attempts were OFF and the second had correction guidance and human extraction repairs. It can serve as a bounded documentation comparison with the same pinned evidence, checker, and review across modes.

The W75 rejection concerned a stray file and source/scope errors. The existing record supports that specific diagnosis. Replays should use the pinned pre-landing checkouts without reopening completed backlog rows.

## Provenance

The [source hash manifest](SOURCES.sha256) includes the raw backend logs, both Performance JSON reports, both canary matrices and the independent outcome sources. The [reconciliation script](audit_tokens.py) verifies current raw hashes against PERFORMANCE, checks all attempt and logical-task counts, reconciles native timings with available API usage, and generates the tables.

Next: Main uses the paired records and objective checks to interpret authorized rerun results.
