# wiki3b dive

Title (page): Karpathy's LLM Wiki Gist Decoded: What I Added (URL slug: i-rebuilt-karpathys-llm-wiki-heres; page was retitled/updated, has June 2026 update note)
Author: Eugeniu Ghelbur (theaioperator.io, Substack). Date: 2026-04-29. Reachability: HTTP 200, 18301 chars stripped.

| # | section | quote | quote_sha256 |
|---|---|---|---|
| 1 | Why a conceptual blueprint is not a working second brain | "This works for the first 50 to 100 sources. Past that, three failure modes compound: claims go stale, contradictions accumulate faster than you resolve them, and the cross-reference graph becomes too dense to navigate manually." | 192a93f0828b96114ed8384d5d69e032d4905540871170c6e3c784bef229acee |
| 2 | What I got wrong | "Three small bugs, but together they meant the command designed to make my vault smarter  was making it dumber on its first run." | 876563f3d3f34f4b94b884b1a3a009785dec40414d94631037e18cf44fb101de |
| 3 | What I got wrong / Five things #4 | "Every scheduled agent in this rebuild logs its changes to a daily diff note and waits 24 hours before any change becomes permanent." | 63e3662707ed3a039b7f2d97301b74be8e8b843778548369cc5ea0a91d5e8f2a |

Notes: the quote in row 2 contains a literal newline in the stripped text; hash is over the exact stripped substring.
Numbers: 50-100 sources (append-only works), 'few hundred' (breaks), 24h delay before permanence, 31 slash commands, 4 scheduled agents, 6 months run, costs $0.04-$0.80/call. All are author assertions/config; none is a measured benchmark. No eval of contradiction rate, orphans, or staleness.
'Three bugs in v1' = /research-deep bugs: wrong Perplexity model gave 10,000-word report; <think> tags saved verbatim; frontmatter stored stringified Python dicts. Not a wiki-architecture bug; fix = reversibility (daily diff log, 24h hold).
Fixes: provenance = source URLs verbatim, recency markers, confidence frontmatter, superseded entries kept dated (not measured). Contradictions = auto-reconcile by recency/authority/confidence, loser archived with explanation (design, unmeasured). Orphans = weekly health check finds orphaned notes/dead links/stale pages. Human review = none upfront; 24h delayed commit + diff notes serve as review window. Cites rohitg00 v2 (confidence, supersession).
