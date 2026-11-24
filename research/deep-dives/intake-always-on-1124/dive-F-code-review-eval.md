# Dive F-code-review-eval (intake run always-on-1124, 2026-11-24)

Stage-2 deep dive. Sources were read from the retained anchor snapshots through the machine_anchor extractor; every anchored quote is an exact substring of that text and carries a script-written anchor_mark in the index. In-house reads at epyc-root 3b11e6c82 (no drift to a290df6 on the cited files) and epyc-inference-research 82d5822.

## intake-2955: How the Claude Code team does code review (Addy Osmani, Morgan Westlee Lunt, Qing Wang, Anthropic, 2026-10-15)

- URL: https://claude.dev/blog/solving-code-review-at-anthropic/
- Read depth: FULL
- Verdict: adopt_patterns; relevance high; credibility 2

| # | Claim | Status | Locator |
|---|---|---|---|
| 0 | The reviewer evaluation is built from past PRs that caused incidents, with their fix-forwards and reverts, each bug confirmed by engineers who know the code, and it runs daily. | CONFIRMED | How we make the reviewer better |
| 1 | A known-clean PR control counts how often the reviewer would have led someone to a harmful change. | PARTIAL | How we make the reviewer better |
| 2 | The only A/B test described is of the finding filters on the team's own PRs; no tuning/test split of the incident set is described. | CONFIRMED | AI review on every pull request |
| 3 | Recall is tracked alongside rounds-to-pass, but no recall value or measured stage is reported. | PARTIAL | How we make the reviewer better |
| 4 | Reviewer noise is measured by how the PR author responded to each comment: fixed, wrong, intentional, or did not matter. | CONFIRMED | How we make the reviewer better |
| 5 | Revert and incident rates are guardrails on claimed human-time savings; circuit breakers that tighten approval do not exist yet. | PARTIAL | The scarce resource |

Claim notes:

- [0] Set size, case count and scores are not given.
- [1] Size-matching and how clean is established are not stated.
- [2] Reviewer changes are kept if the score on the whole incident set goes up, so the set is both tuning target and test.
- [3] No recall number, denominator or pipeline stage.
- [4] Author response is a noisy label, especially when the author is an agent.
- [5] The 40% fall in reverted share is a before/after with no control.

Dive record: 2026-11-24 Stage-2b wave 2 (dive F, sonnet, FULL): 6 claims, 3 CONFIRMED, 3 PARTIAL. It narrows intake-2943 claim 4: the incident-derived answer key and the clean control are real, but the tuning/test split, size-matching and per-stage recall that intake-2943 describes are not in this post. Live-lesson test: L5 agrees (mechanical evidence first; an agent's approval never counts as a person's). Gap it exposes in-house: none of our verifiers (the taskflow reviewer fall-through in verify.py, the AutoKernel keep gate, the intake second reader) is graded against past reverts or incidents. Dive-surfaced source declined at the two-wave cap: the Code Review announcement post (no URL in the text); intake-2943 is its parent, already dived.

Contradicting or limiting evidence:

- No held-out split: the incident set accepts or rejects reviewer changes and is also the score.
- intake-2943 attributes a tuning/test split, a merged-and-stable control and per-stage recall to this post; none of these appears in the linked post as fetched 2026-11-24.

