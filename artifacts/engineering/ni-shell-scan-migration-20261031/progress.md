# Progress — scanner migration — 2026-10-31

- Added canonical `shell_scan.lex()` and retained `segments()` as an identical-signature compatibility wrapper.
- Migrated exactly the three approved scanner modules.
- Added ten-case baseline/current semantic parity controls; only the documented pytest comment false-positive differs.
- Added shared lexer cases and actual hook end-to-end controls for malicious real invocations after heredocs.
- Normal hooks passed. Source/tests `c5c87541f32ce16fdb7b8464038739a8bdc0105d` and closure/artifact commit `3a9dcf588f143b87688d1e6996b22f6b77312abf` are on `origin/main`; ancestry verified after fetch.
- R6 validation passed: 129 passed, zero skips, physical CPU region 32–33, effective CPUs 128–129, OMP 1, peak sampled RSS 56,152,064 bytes, 5.077 s, PID absent after wait. Initial missing-pytest setup refusal is preserved separately.
- Packet path: `artifacts/engineering/ni-shell-scan-migration-20261031/`.
- Citation correction: MAIN updated the original handoff line to the Git-verified source commit `c5c87541f32ce16fdb7b8464038739a8bdc0105d`; verified with `git rev-parse` and `git cat-file`. Original 129-pass R6 result remains unchanged; no tests were rerun for this citation-only correction.
