# Intake run always-on-1124 (2026-11-24)

Source: "Building always-on agents" (Anthropic, 2026-11-13), intake-2942, with 10 Stage-1 expansions (intake-2943..2952) and 3 Stage-2b wave-2 sources (intake-2953..2955). Operator pre-authorised every recommended dive for up to two Stage-2 waves.

## Files

- `dive-A-inbox-outbox.md`: intake-2942, 2950, 2951, 2952
- `dive-B-verification-loops.md`: intake-2943, 2944, 2945
- `dive-C-permissions-deferral.md`: intake-2947, 2948, 2949
- `dive-D-memory-autopilot.md`: intake-2946 (plus the memory sections of intake-2942)
- `dive-E-agent-time.md`: intake-2953, 2954 (wave 2)
- `dive-F-code-review-eval.md`: intake-2955 (wave 2)
- `stage3-plan.md`: the Stage-3 plan, pending operator approval

## Main findings

- The article's run cycle (event inbox, timers, memory, permissions, outbox) already exists in parts of our stack: the session bus is an at-least-once inbox with id dedup, rowflow resumes rows, the AutoKernel loop resumes from its store, and the orchestrator autopilot resumes each cycle from durable state.
- Gaps it exposes: rowflow claims bypassed the planner until a reservation planner shipped in shadow on 2026-11-24 with no owner box; the Codex lane drivers stop on the lane's own LANE-STATUS line instead of artifacts; taskflow has no resumable end state and no count of early-ended units; no verifier (AutoKernel keep gate, taskflow reviewer, intake second reader) is graded against past failures.
- Corrections: intake-2943's description of the code review eval (tuning/test split, per-stage recall) is not in the post it links (intake-2955); the AgentTime 4%/63% figure that intake-2950 cites is exact but measures following a requested duration; the 78% Opus cost figure in intake-2942 is a vendor self-report on an unnamed benchmark.

