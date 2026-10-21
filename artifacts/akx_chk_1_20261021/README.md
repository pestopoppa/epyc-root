AKX-CHK-1 reproduction (2026-10-21). `chk1_truncated_op_suite_repro.py` feeds `parse_backend_ops_console` a test-backend-ops
console cut off between two cases (a wall-clock kill) and calls `reconcile()`. Observed output (run 2026-10-21 against
epyc-inference-research 48ffc3499):
`parsed without error; exercised: ('MUL_MAT', 'MUL_MAT_ID') cases_by_op: (('MUL_MAT', 1, 1), ('MUL_MAT_ID', 1, 1)) failed: ()`
A kill inside a case line is refused (OutputParseError); a kill between cases reads as a clean pass.
Run with the orchestrator venv python from a checkout of epyc-inference-research.
