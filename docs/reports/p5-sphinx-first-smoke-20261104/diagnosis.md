The first smoke is FAIL, not scorer PASS. Original native pytest output reports
2 failed, 1 passed; unchanged pinned official get_logs_eval parses both named FTP
failures but no named PTP because pytest emitted F.F progress and failure-only
summary. tox -v controls tox verbosity, not pytest. Sphinx maps to official
parse_log_pytest_v2, whose accepted formats start/end with named status tokens.
ANSI failure summaries parse correctly; the missing named PASSED line is decisive.
Both FTP failures are authentic expected negative outcomes. Gold did not run.
Owned container cleanup passed. Original result, output, report and producer
sources are retained byte-for-byte. Successor adds only pytest reporting flags
-rA --color=no to the exact original tox test command; no selectors, patches,
parser change. Scoring thresholds stay unchanged. Successor completion semantics intentionally distinguish a fully observed diagnostic FAIL from infrastructure/partial refusal; ERROR/SKIPPED named statuses refuse completion. No model execution.
