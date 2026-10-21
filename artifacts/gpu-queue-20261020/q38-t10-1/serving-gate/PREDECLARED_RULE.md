# Q38-T10.1 serving gate: predeclared decision rule

Operator ruling: 2026-10-21T09:08:36Z. Recorded by main before main had seen any serving-gate result.

**Rule: Net, paired.**
- Over the 80-prompt corpus (sha 224e7d92…), count the discordant pairs: R = prompts that pass spec-off and fail spec-on (regressions); G = prompts that fail spec-off and pass spec-on (gains).
- **FAIL** if a one-sided exact McNemar/sign test of R vs G gives p < 0.05, where H1 is that regressions exceed gains. Otherwise **PASS**.
- The strict reading ("any regression fails") is reported for information only and decides nothing.
