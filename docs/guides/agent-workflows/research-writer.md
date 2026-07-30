# Research Writer Workflow

Canonical workflow for the research-writer role (`agents/research-writer.md`). This file
absorbed the former agents/research-writer-guide.md (retired 2026-07-30 — it duplicated this
doc, targeted a report file that no longer exists, and used subagent @-mention wiring that was
never installed).

## Primary Script

Use `scripts/utils/report_update_workflow.sh` (in `epyc-inference-research`) to gather validated
source data before writing updates. The report it maintains is
`repos/epyc-inference-research/docs/reference/benchmarks/RESULTS.md` (the script's
`REPORT_FILE`).

## Common Commands

```bash
bash scripts/utils/report_update_workflow.sh --benchmark logs/<file>.csv   # benchmark-driven update
bash scripts/utils/report_update_workflow.sh --track "Track N" "<status>" "<details>"
bash scripts/utils/report_update_workflow.sh --summary    # full refresh context
bash scripts/utils/report_update_workflow.sh --validate   # consistency check
bash scripts/utils/report_update_workflow.sh --show       # print current report
```

## Dispatch Template

When dispatching a writing task to a session acting in the research-writer role, include the
workflow output and require:

1. New benchmark table rows (claims follow the measurement grammar — protocol id, n, date, attest)
2. Interpretation of the acceptance-vs-speed tradeoff
3. Updated recommendation section
4. Source paths and timestamps

## Definition of Done

1. Every quantitative claim maps to a source artifact.
2. Status labels match the latest validated outcomes.
3. Reproduction details are present for key results.
4. Validation failures are either fixed or explicitly documented.
