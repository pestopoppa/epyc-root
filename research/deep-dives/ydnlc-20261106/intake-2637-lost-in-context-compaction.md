# intake-2637 — Lost in Context Compaction (arXiv 2608.11242v2)

**Dive date**: 2026-11-06 · **Read depth**: FULL · **Revision**: v2 (2026-10-11)

## Results

- A **side constraint** is a user-issued requirement governing *how* a task is carried out; removing it leaves the
  primary goal intact but changes acceptable behaviour. Five types: Action, Information, Process, Preference, Output.
- Retention is measured separately from task success through a baseline-corrected effective-retention score. The
  paper reports **no task-success metric**, so it cannot support "task accuracy unaffected".
- **17% average retention is misleading for us**: it reproduces only when GPT-5.4-mini 220K cells are included.
  **Open-weight compactors retain 6.06%.** No compactor exceeds 28.6% on the natural SWE-Natural set.
- Restatement after compaction cuts violations 30%→13% but does not eliminate them (no failure had explicit user
  approval). The only mitigation above 90% is an **out-of-transcript extract-and-append registry** (90.3–95.1%
  retention, 93.4–96.3% compliance). External enforcement is explicitly future work.
- **NOT-FOUND**: any experiment placing a constraint in the system prompt. Every injection is a user turn, and the
  stitching method strips extra system prompts. Compactor instructions lift retention but stay below 40%.

## EPYC actionables

| Action | Owner | Disposition |
|---|---|---|
| Add a post-compaction rule-retention probe as a co-metric on CF-3c, declared before any run | context-and-token-economy.md | adopt-design |
| Fix the inverted reference-miss detector before trusting any retention number | context-and-token-economy.md + session_summary.py | adopt-now |
| Promote machine-checkable rules into deterministic deny lists; keep the rest in an out-of-transcript registry appended at compaction | harness-program.md + opencode config | adopt-partial |
| Gate any compaction enable on a measured retention number for the rule-heavy role | context-and-token-economy.md | gate |

## Surfaced

2609.26682 access-control framework (wave 3); 2606.16038 SWE-Natural corpus (not dived).
