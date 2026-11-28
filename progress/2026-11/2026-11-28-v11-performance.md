# v11 performance closeout priorities

[PR #3](https://github.com/pestopoppa/epyc-root/pull/3) merged at `cc46d17b3`. It brought the W66 timing, prefix-quality observations and kernel verdicts to main. The hosted hermetic suite had the same 14 belief-substrate failures on the PR and the preceding main run. The landed handoff index passed its local check.

The [v11 performance plan](../../docs/reports/v11-performance-closeout.md) records the MI210 N10 numerical gate, the separate Q38FN CPU host-depth gate and the model-specific serving choices. The kernel owner has a [C22 N10 brief](../../handoffs/active/briefs/MMID-HELPER-N10-GATE.md). RTG-02 has a [natural-work quality brief](../../handoffs/active/briefs/AP-W66-PRESERVE-QUALITY.md) for A3B prefix preservation. The 256/900 result is retained as a measured latency tradeoff. This filing added one open task and supplied a brief for an existing task.

Next: the kernel owner prepares the N10 comparison and RTG-02 qualifies the frozen quality controls before the paired A3B run.
