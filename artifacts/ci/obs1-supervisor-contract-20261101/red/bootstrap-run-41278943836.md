# Workflow bootstrap failure

Run 41278943836 (commit `7f08d858b2f137411ce31c579b103456abe57554`) failed before job creation: GitHub annotation was `Invalid workflow file ... Line 24, Col 24: Unrecognized named-value: runner. Located at position 1 within expression: runner.temp`. It had zero jobs, no test process, and no artifact. The workflow-only follow-up moved result-directory setup into the shell step.
