# DCP-15 classification (2026-11-09, apr2 third-pass; zero inference, read-only over the recorded tap)

Sample: all 20 architect_critic and all 24 non-identical architect_general pairs of
`artifacts/noninf-memeval-20261021/dcp14_result.json`, re-derived with the DCP-14 detector's own
pairing (counts reproduce: 20 / 24 / 6 identical). Per-pair list: `dcp15_pair_classification.json`.
Each pair was read (parent prompt head, child prompt head, dropped items).

| Parent prompt kind | architect_critic | architect_general | Dropped constraint needed by the worker? |
|---|---|---|---|
| fixed plan-review template (`Review plan. Reply JSON ONLY: {"d":...}`, 761-782 chars) | 20 | 22 | No. The constraints are the plan-reviewer's own reply schema and patch format; the child is an unrelated benchmark task (MMLU-Pro, BigCodeBench, LiveCodeBench, ...). The parent never authored the child prompt. |
| `Respond with ONLY valid Python code. No explanations...` + task text | 0 | 2 | Plausibly yes (worker output is code), the only 2 of 44 candidates for a real drop: the child carries the task text without the preamble. |

Findings:
1. The 0.043 schema-key and 0.040 / 0.000 non-identical rates are dominated by a PAIRING ARTIFACT.
   The detector pairs each worker call with the latest non-delegate call in the same
   `parent_request_id` group; in these groups that call is the plan-review step, whose prompt is a
   constant template, not a prompt that wrote the worker's prompt. 42 of 44 pairs measure
   "plan-review schema absent from an unrelated task", which is not a defect.
2. Of 44, one child (architect_general #19, an IFEval-style prompt) carries its own format constraint
   unrelated to the parent; none shows a needed schema key dropped.
3. Real candidates: the 2 `python_only_preamble` pairs. N=2 supports no rate; treat as a lead.

Specification for (2), where the constraint block is carried: a delegate prompt must carry its output
constraints in a structured field of the delegation record (`output_constraints`: `{format: [...],
schema_keys: [...]}`) written by the AUTHOR at delegation time, with the prose prompt rendering from
it. DCP-14 then re-runs against that field instead of regex-extracting from prose, and a
delegate-authored pair is identified by the field's presence (no inference from request-group
co-membership). Until then DCP-14's detector should require the parent prompt to contain (a
normalized substring of) the child task text before a pair counts as an authored delegation.
No fix is assumed or implemented here.
