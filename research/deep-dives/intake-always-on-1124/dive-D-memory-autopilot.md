# Dive D-memory-autopilot (intake run always-on-1124, 2026-11-24)

Stage-2 deep dive. Sources were read from the retained anchor snapshots through the machine_anchor extractor; every anchored quote is an exact substring of that text and carries a script-written anchor_mark in the index. In-house reads at epyc-root 3b11e6c82 (no drift to a290df6 on the cited files) and epyc-inference-research 82d5822.

## intake-2946: The components of agent memory (Lance Martin, Anthropic, 2026-11-06)

- URL: https://www.anthropic.com/research/components-of-agent-memory
- Read depth: FULL
- Verdict: adopt_patterns; relevance high; credibility 3

| # | Claim | Status | Locator |
|---|---|---|---|
| 0 | Strategy, plans and tested rules exist only if the agent works them out and writes them down; state readable each turn need not be stored. | CONFIRMED | Claude has learned to judge salience |
| 1 | The top memory layer is injected every session and must stay small; Claude Code loads only the first 200 lines or 25 KB of MEMORY.md. | CONFIRMED | Dreaming can promote notes up the memory hierarchy |
| 2 | Dreaming can correct a wrong note by checking it against the original transcript. | PARTIAL | Dreaming can correct memory |
| 3 | Wikis built by dreaming help most when paired with search: 13% to 48% of graded criteria from 2 to 128 sessions on 25 questions. | CONFIRMED | Dreaming can build new memory representations |
| 4 | For stronger models, freedom to judge salience beat fixed rules set in advance. | CONFIRMED | Steering Claude to write memory |
| 5 | Concurrent writers to one shared page lost facts; one writer per page fixed it. | CONFIRMED | Dreaming can focus memory on a specific goal |
| 6 | Logging notes in the moment distracts from the main task, while background dreaming is not immediately available. | CONFIRMED | Thinking backward, looking forward |

Claim notes:

- [0] Evidence is one run per model (Sonnet 3.7: 413 files in 225 folders, 1 badge; Fable 5: nine files, 4 badges).
- [1] The threshold is stated, not measured.
- [2] One anecdotal scenario, no repeated trials.
- [3] Search plus wiki 54% to 61% versus 53% search alone; no gain where one document sufficed.
- [4] The per-model gains are in figures and not in the text.
- [5] 41 of 57 facts survived versus 57 of 57 after the fix.
- [6] Stated tradeoff, no measurement.

Dive record: 2026-11-24 Stage-2 wave 1 (dive D, sonnet, FULL): 7 claims, 6 CONFIRMED, 1 PARTIAL. Live-lesson tests: L1 adds (in-the-moment progress logging distracts the worker; a harness- or coordinator-side writer that derives progress from artifacts avoids that); L5 agrees (validate memory against recorded artifacts, n=1); L3 weakly agrees (one writer per page). The memory-index size check the dive proposed was settled by the integrator: 97 lines, 20,039 bytes, inside the stated window, so no action. Dive-surfaced source: Sleep-time compute (arXiv 2504.13171) is already indexed as intake-819; cross-reference only, not re-ingested.

Contradicting or limiting evidence:

- Vendor evaluations on vendor models; the Pokemon comparison is one run per model.
- Wiki alone underperformed search plus wiki, and one wiki grew larger than its raw files.

