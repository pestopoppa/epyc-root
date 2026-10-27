# Post-measurement analysis: mandatory after every row ends

Why: an exit code says the process stopped. It does not say what was learned. A result that never
reaches project context (the owning handoff, the belief kernel, the wiki, follow-up work) is a
measurement run blindly.

Origin: on 10-27 KVU-16b, CH-26a and the night chain were reported as "passed" with no verdict
read. The operator: *"Let's not run measurements blindly … results MUST be placed into project
context … belief kernel injections, wiki, and follow-up work"*.

Run this on every `.ended`, `.complete` or FAILED. Finish it before the next operator report;
granting the freed bin may go ahead first.

## Checklist

1. **Read the verdict, not the rc.** Open the VERDICT / RESULT / report file and read the
   individual gate lines. A summary PASS can hide a failed gate (SKILL §4).
2. **Extract the metric against its predeclared rule and direction**: higher or lower is better,
   the threshold, and the noise floor with its unit. If no rule was predeclared, say so and file it
   as a defect of the row.
3. **Classify** the row as exactly one of the following:
   - `capability`: a new thing works;
   - `performance`: keep or no-keep against the rule;
   - `reject`: the rule failed;
   - `correctness-only`: a gate with no metric;
   - `invalid`: the run does not measure what it claims (harness fault, wrong binary, window miss).
4. **Update the owning handoff box.** Add a dated result sub-bullet
   (`- 2026-10-27: <metric> vs <rule> → <class>`). Tick the box only when its exit criterion is
   fully met, and file follow-up child `- [ ]` boxes.
5. **Add a progress line** in `progress/YYYY-MM/YYYY-MM-DD.md`.
6. **Belief.** Note the projection readiness in the matching `VB-*` task of
   `handoffs/active/vidya-belief-substrate-program.md`, and list committed-conclusion register
   candidates. The tick carries `[belief: …]` or `[no-belief: <reason>]`.
7. **Wiki.** List wiki-page candidates for the next compilation sweep.
8. **Report the meaning.** Every status or progress report states what each result means, for
   example `KVU-16b: +3.1 % t/s vs ≥+2 % rule → performance keep`, and never only "passed" or
   "rc 0".
