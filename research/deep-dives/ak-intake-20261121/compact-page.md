# CompAct-Bench project page (intake-2778) - Stage-2b dive
Source: https://compaction-eval.github.io/CompAct-Bench/ fetched 2026-11-21; read_depth FULL; lane_head ac1347f5d3218531bb369c286837630bf842ff74. Bears on intake-2762 (2611.25673v1/dive.md read first).

## Verdict
The page releases nothing. Raw HTML links only: the paper PDF (assets/compact-bench-paper.pdf), author scholar pages, chenlizhe.cn, workbuddy.cn, KaTeX/fonts. No GitHub, HF, dataset, license or IRC prompt link (grep of raw page.html in extra/compact/). The page's interactive figures are "sampled from the paper's mean accuracy" (simulation).

## Claim verification
| Question | Result |
|---|---|
| Data released? | NOT-FOUND-IN-SOURCE (no link) |
| Executor harness released? | NOT-FOUND; Table 6 names search_agent / swe_agent / companybench_agent with closed executors (Opus 4.8, GPT-5.5 Codex) |
| IRC prompt released? | Not on page; paper Appendix A.2 holds the prompt text (per prior dive); PDF not text-extractable here |
| License? | None stated (copyright line only) |
| CompanyBench? | Internal ("an internal CompanyBench suite") - withheld |

## Principles
Protocol principle only: fix task/boundary state/budget, vary M_b, enforce 10% retention (IRC, tolerance [0.097,0.103]). Device-agnostic; run cost is executor inference (MI210 or CPU quarter). Cost M, consumer TOC-CMP-4.

## Grounding
Prior dive A3 (handoffs/active/context-and-token-economy.md, TOC-CMP-4) gated on "release confirmed": now settled negative for linked artefacts. Searched: raw page.html, extracted.txt.

## Adversarial
Page is the authors' own presentation; no independent replication found in this pass (no search needed: zero release surface). Restatement of the paper otherwise.

## Actionables
compact-page-A1 task: make A3 self-built (reimplement IRC, own instances). compact-page-A2 decline: CompanyBench/leaderboard as data.

## Dive-surfaced
Paper PDF: decline (already dived as 2611.25673v1).

artifact audit: clean
