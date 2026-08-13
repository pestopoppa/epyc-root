# mainA — ODL PaddleOCR parser-comparison (row L557)

**You are mainA** (roster id `mainA`, lanes `[cpu, none]`). Bootstrap: `drain --agent mainA --triage`, then execute.

Row `opendataloader-pipeline-integration--PaddleOCR-L557` (`handoffs/active/opendataloader-pipeline-integration.md:585`):

> Compare LightOnOCR or another table-competent parser arm against the current ODL/PaddleOCR
> evidence on structural / table / reading-order metrics.

First assess whether this needs a **new run** (parsers over the corpus → compute) or can be done
against **already-collected evidence** on disk.

- If it needs a run, do NOT self-acquire compute — file a `compute-request` to `inference`
  (`kind: compute-request` is now in the schema; name task + window + device/region + `est_h` +
  release-condition) and, while waiting, do any non-compute prep (metric definitions, comparison
  harness, existing-results inventory) per rule 2 (never block on the bus).
- If existing evidence suffices, produce the comparison table now.

## Constraints

- lanes `[cpu, none]`: CPU/GPU work only via a compute window **granted by inference** (rule 11).
- **Push policy (operator 2026-08-13): docs/handoffs pushes PERMITTED**; hold kernel/orchestrator
  code pushes.
- Wrap up at the boundary (flip checkboxes, commit, push handoff edits).
