# FM-2 fixed-catalog AdaMAST grading pilot

On 2026-11-18, the pilot returned one valid structured grade for each of 23 traces
across eight Claude and Codex strata. MAST-12, “No or incomplete verification,”
was the most frequent judge label, assigned to 14 of 23 traces. This is a
description of the frozen sample and judge outputs.

## Sample and execution

The sampling frame was eligible, present local JSONL files enumerated by the
committed FM-2 sampler. Rotated transcripts and sessions outside that enumeration
were outside the frame. The seeded sampler took up to three files from each observed
harness, month, and main/subagent combination. The October Codex subagent stratum
had two eligible files. Normalization stripped outcome fields and retained the
observable trajectory. Each trace was graded with a 12,000-character trace cap and
a 1,536-token output cap. [Frozen sample manifest](../../data/fanout_timing/fm2_adamast_provenance.v1/manifest.json)

| Harness | Month | Session | Eligible files | Planned | Attempted | Valid |
|---|---|---|---:|---:|---:|---:|
| Claude | 2026-10 | Main | 5 | 3 | 3 | 3 |
| Claude | 2026-10 | Subagent | 1,555 | 3 | 3 | 3 |
| Claude | 2026-11 | Main | 11 | 3 | 3 | 3 |
| Claude | 2026-11 | Subagent | 1,604 | 3 | 3 | 3 |
| Codex | 2026-10 | Main | 3 | 3 | 3 | 3 |
| Codex | 2026-10 | Subagent | 2 | 2 | 2 | 2 |
| Codex | 2026-11 | Main | 159 | 3 | 3 | 3 |
| Codex | 2026-11 | Subagent | 193 | 3 | 3 | 3 |
| **Total** | | | **3,532** | **23** | **23** | **23** |

The judge was Qwen3.8-27B Q8_0 through the AdaMAST CLI at upstream commit
`3c83d81c85937f5e8911fd96daa2ca38c1ad2585` with the pinned local patch and
14-code taxonomy. One private CPU v10 server (build 10303, commit prefix
`ffc1bac82`) served the pilot on CPUs 48–71 with 24 threads, with thinking and
retries disabled. The first unit started at 12:20:19 UTC and the last receipt
finished at 13:24:38 UTC. The final unit receipt satisfied the completion rule.
The failure stop rule was more than 25% failed receipts after at least eight
attempts. [Execution packet](../../scripts/experiments/fm2-adamast/README.md),
[runtime receipts](../../data/fanout_timing/fm2_adamast_results.v1.jsonl)

## Judge labels

Counts are the number of valid traces assigned each code. Each trace counts at
most once per code and can carry multiple codes. Four of 23 returned
`none_apply`. Wilson intervals shown here are the native 95% binomial intervals,
rounded to one decimal percentage point. They describe the pooled sample under
that calculation and carry no fleet or subgroup inference.

| Code | Label | Count / valid | Wilson 95% |
|---|---|---:|---:|
| MAST-1 | Disobedient to task specification | 2 / 23 | 2.4–26.8% |
| MAST-2 | Disobedient to role specification | 0 / 23 | 0.0–14.3% |
| MAST-3 | Step repetition | 0 / 23 | 0.0–14.3% |
| MAST-4 | Loss of conversation history | 0 / 23 | 0.0–14.3% |
| MAST-5 | Unaware of termination conditions | 0 / 23 | 0.0–14.3% |
| MAST-6 | Conversation reset | 0 / 23 | 0.0–14.3% |
| MAST-7 | Failure to ask for clarification | 1 / 23 | 0.8–21.0% |
| MAST-8 | Task derailment | 2 / 23 | 2.4–26.8% |
| MAST-9 | Information withholding | 0 / 23 | 0.0–14.3% |
| MAST-10 | Ignored other agent's input | 2 / 23 | 2.4–26.8% |
| MAST-11 | Premature termination | 6 / 23 | 12.5–46.5% |
| MAST-12 | No or incomplete verification | 14 / 23 | 40.8–77.8% |
| MAST-13 | Weak verification | 5 / 23 | 9.7–41.9% |
| MAST-14 | Incorrect verification | 0 / 23 | 0.0–14.3% |

There were zero failed, interrupted, or parse/schema-invalid receipts. All 23
HTTP journals contain a 200 response with one choice ending in `stop`. Zero of
23 had a nonempty structured `refusal` field. The response format omitted that
field in every journal, so this records explicit refusal signals only. All 23
returned usable structured diagnoses, including the four `none_apply` grades.
[Native summary](../../data/fanout_timing/fm2_adamast_summary.v1.json),
[per-unit diagnosis and response metadata](../../data/fanout_timing/fm2_adamast_diagnosis_projection.v1.jsonl)

## Interpretation and F-series crosswalk

Two or three grades per stratum give little resolution for harness, month, or
role comparisons. The pooled counts describe an approximately balanced stratified
sample with sharply unequal eligible populations across strata. A single capped
view per trace and one judge pass leave label stability unmeasured. Human gold
labels and an independent outcome oracle were absent, so task accuracy, judge
faithfulness, and the effect of fan-out remain unmeasured. This pilot supplies no
Stage 2 advancement evidence.

The frozen crosswalk exists and matches the packet digest. It proposes nine
symptom overlaps and lists five MAST codes as unmapped. MAST labels describe
within-trace symptoms, while the F-series ledger records coordinator behavior
with its own context, root causes, and remediations. The original mapping came
from reading code names and short ledger descriptions. The pilot ran MAST
grading only and supplies no validation of those proposed links.
[Frozen proposed crosswalk](../../data/fanout_timing/fm2_adamast_provenance.v1/mast_fseries_crosswalk.json)

## Evidence files

- The [native receipt JSONL](../../data/fanout_timing/fm2_adamast_results.v1.jsonl)
  and [native summary](../../data/fanout_timing/fm2_adamast_summary.v1.json) are
  byte-for-byte copies. Each receipt records source and normalized trace digests,
  hashes of the original diagnosis and HTTP journals, and runtime binary,
  loaded-library and grant identities.
- [Original per-unit diagnoses](../../data/fanout_timing/fm2_adamast_native/units)
  retain the judge's evidence text. The compact [diagnosis projection](../../data/fanout_timing/fm2_adamast_diagnosis_projection.v1.jsonl)
  preserves code assignments and HTTP refusal metadata for recomputing the
  counts without reading that text. The diagnoses and response journals were
  checked against their receipt hashes.
- The [provenance directory](../../data/fanout_timing/fm2_adamast_provenance.v1)
  preserves the sample manifest, taxonomy, proposed crosswalk, prepared spec,
  runtime pins, and packet, kernel and model checksums. The input traces and
  byte-exact HTTP journals remain in the retained scratch packet at
  `/mnt/raid0/llm/tmp/coordination-and-churn-pipeline/fm2` under `inputs/traces`
  and `out/units`, respectively. Request and response byte replay depends on
  that scratch packet. The model is identified by digest and remains in the model
  store.
