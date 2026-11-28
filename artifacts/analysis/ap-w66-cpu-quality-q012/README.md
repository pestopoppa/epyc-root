# Dedicated q0–q2 real-task quality comparison

The [report](../../../docs/reports/autopilot-w66-cpu-quality-q012.md) explains the paired W66 continuations. [Summary](summary.json) contains the complete first-request receipts, terminal snapshots, closed-wire reconciliation, independent verdicts, resource checks and cleanup.

EVIDENCE.tar.gz contains the exact runners, checkpoint database, protocols, native server logs, all final wire request bodies/receipts, restored/exported sessions, source bindings and independent grading logs. Setup attempts have distinct member prefixes. ARCHIVE-MANIFEST.json binds each decoded member. Original baseline source remains pinned by the case and repository commit. The grader sources and control verdicts are retained.

Verify SHA256SUMS, then verify decoded member SHA-256 against ARCHIVE-MANIFEST.json. Replaying inference requires the same C22 CPU build, model, frozen OpenCode runtime and case inputs named in the recorded runners. Keep CPUs 0–71 and memory nodes 0–2 throughout. The snapshot database and source checkpoint support reconstruction; the paired raw first requests provide the comparison identity.

Warm-prefix reconstruction took 355.71/354.37 seconds OFF/ON and is reported separately from each 600-second working window. Preserve original terminal counts and the late native counters as different observations. Both initial deadline and follow-up interruptions remain visible.
