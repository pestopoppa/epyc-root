# Progress — scanner migration — 2026-10-31

- Added canonical `shell_scan.lex()` and retained `segments()` as an identical-signature compatibility wrapper.
- Migrated exactly the three approved scanner modules.
- Added ten-case baseline/current semantic parity controls; only the documented pytest comment false-positive differs.
- Added shared lexer cases and actual hook end-to-end controls for malicious real invocations after heredocs.
- Normal hooks passed and source/tests were committed as `c5c87541f4b487ad4f44df89b3cf9549eee7fc02`; source commit is waiting for the MAIN-owned original handoff closure and joint publication.
- R6 validation passed: 129 passed, zero skips, physical CPU region 32–33, effective CPUs 128–129, OMP 1, peak sampled RSS 56,152,064 bytes, 5.077 s, PID absent after wait. Initial missing-pytest setup refusal is preserved separately.
- Packet path: `artifacts/engineering/ni-shell-scan-migration-20261031/`.
