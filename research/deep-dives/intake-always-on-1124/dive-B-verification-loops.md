# Dive B-verification-loops (intake run always-on-1124, 2026-11-24)

Stage-2 deep dive. Sources were read from the retained anchor snapshots through the machine_anchor extractor; every anchored quote is an exact substring of that text and carries a script-written anchor_mark in the index. In-house reads at epyc-root 3b11e6c82 (no drift to a290df6 on the cited files) and epyc-inference-research 82d5822.

## intake-2943: How the Claude Code team thinks about verification (Addy Osmani, Anthropic, 2026-11-16)

- URL: https://claude.dev/blog/how-the-claude-code-team-thinks-about-verification/
- Read depth: FULL
- Verdict: adopt_patterns; relevance high; credibility 2

| # | Claim | Status | Locator |
|---|---|---|---|
| 0 | End-to-end, property and differential tests are the three types worth investing in, and end-to-end is the one to pick if only one. | CONFIRMED | Not all tests are created equal |
| 1 | The rules that judge a change live where the change cannot edit them (read from the base branch). | CONFIRMED | Changes can’t modify their own checks |
| 2 | A new commit gate starts in observe mode, logging what it would have blocked so false positives can be reviewed; after two blocks in a session the next commit passes. | CONFIRMED | Start a new gate in observe mode |
| 3 | After three failed fix rounds the agent stops and brings in a human. | CONFIRMED | Failing tests require human attention |
| 4 | Verifier quality is measured with a tuning set kept apart from a fixed test set. | PARTIAL | Test your checks on what actually matters |
| 5 | Each commit is stamped with how it was verified, including none. | CONFIRMED | Changes can’t modify their own checks |
| 6 | Property tests keep agents honest because their edge cases do not share the authoring agent's bias. | CONFIRMED | Not all tests are created equal |
| 7 | Test suites, verification steps and instruction files are pruned on a routine because they only grow. | CONFIRMED | Rule pruning |

Claim notes:

- [0] No measurement behind the ranking.
- [1] Design principle without incident data.
- [2] The gate checks that the session ran /code-review or /verify, which is process evidence rather than artifact evidence.
- [3] A cap on a fix loop, not a resume driver.
- [4] The evaluation itself is in a sibling post (intake-2955); this article reports no recall numbers.
- [5] A queryable record independent of the agent's own account.
- [6] No measurement.
- [7] New rules also need a promotion bar (seen in two PRs, survives three disprover agents, human approval).

Dive record: 2026-11-24 Stage-2 wave 1 (dive B, sonnet, FULL): 8 claims, 7 CONFIRMED, 1 PARTIAL (verifier grading is summarised from intake-2955, dived in wave 2). Live-lesson tests: L4 agrees directly (observe mode before enforce) and adds a bounded-block escape valve that PM-RULES-WARN-FIRST lacks; L5 agrees (checks the change cannot edit; a per-commit verification stamp) and exposes a gap in our own interim driver: drive.sh and drive2.sh stop on the LANE-STATUS line the Codex lane writes itself (drive.sh L14, L23-L24), contrary to README-INTERIM's acceptance-from-artifacts rule; L1 agrees on capped fix rounds; L3 adds routine pruning of accreted rules. Wave 2 (intake-2955) reattributes claim 4: the split and per-stage recall it describes are not in the post it cites. Dive-surfaced source: the linked code review post ingested and dived in wave 2 (intake-2955).

Contradicting or limiting evidence:

- Its verification is tests, review and running the app; it says checks cost few extra tokens, which does not hold for our compute-bound measurement rows where each check takes scarce CPU or MI210 time.

## intake-2944: Automating eval design and hillclimbing with Claude (Lance Martin, Anthropic, 2026-09-28)

- URL: https://claude.dev/blog/automating-eval-design-and-hillclimbing/
- Read depth: FULL
- Verdict: adopt_patterns; relevance high; credibility 2

| # | Claim | Status | Locator |
|---|---|---|---|
| 0 | Each round proposes one patch; train up with test flat means suspected overfitting and a revert. | CONFIRMED | /claude-api hillclimb |
| 1 | Failures are never pasted into the prompt. | CONFIRMED | Overfitting |
| 2 | Noise is checked before the first round, and a gain within noise is reported as such with a recommendation against merging. | CONFIRMED | /claude-api hillclimb |
| 3 | Graders are validated by a human reading sampled scored cases and by running the grader twice on the same output. | CONFIRMED | Validating the grader |
| 4 | On 14 held-out tickets the search never saw, the final configuration scored 90.5% versus 78.6% at about one fifth of the cost. | PARTIAL | Examples: Hillclimbing for cost reduction |

Claim notes:

- [0] The kept code is the version that did best on the test set.
- [1] Plus split cases and answers kept structurally out of reach; no further reward-hacking mechanism.
- [2] No method for estimating noise is given.
- [3] The LLM judge must not be the model under test.
- [4] The 98.9% headline is on the 30 search tickets the hillclimber read; the honest figure is the held-out one (n=14, one ticket is about 7 points, no interval).

Dive record: 2026-11-24 Stage-2 wave 1 (dive B, sonnet, FULL): 5 claims, 4 CONFIRMED, 1 PARTIAL (the 98.9% headline is the search set; held-out is 78.6% to 90.5%, n=14). Live-lesson tests: L5 adds. AutoKernel already accepts from measured artifacts (paired A/B against a calibrated floor, then a serving gate: accumulate.py, bench.py @ 82d5822); the bench-versus-serving split is the train/test split, and the documented bench +5.958% versus serving -2.18% divergence is the overfitting symptom the source describes.

Contradicting or limiting evidence:

- The held-out gain (+11.9 points, n=14) is far smaller than the search-set headline and has no interval.
- Part of the 66.1% to 87.9% skill-eval gain comes from changing graders and tasks inside the loop.

## intake-2945: Using a chaos loop to harden the Claude Docs launch: 60 server errors across billions of requests (Vivek Nair, Anthropic, 2026-11-17)

- URL: https://claude.dev/blog/chaos-loop-claude-docs-launch/
- Read depth: FULL
- Verdict: worth_investigating; relevance medium; credibility 1

| # | Claim | Status | Locator |
|---|---|---|---|
| 0 | The launch saw 60 server errors across 2 billion requests with no rollback. | PARTIAL | Introduction |
| 1 | The service was built so every number the agent measured traced back to the team's own code. | CONFIRMED | Making the service legible to Claude |
| 2 | Before the loop, the human named the decisions needing approval (irreversible ones); everything else ran autonomously. | CONFIRMED | The chaos loop |
| 3 | Invariants held across many compactions without being repeated. | PARTIAL | Why this works now |
| 4 | The effort used about $125,000 of inference at list price. | CONFIRMED | What it cost |

Claim notes:

- [0] Title says billions; the body says 2 billion over the launch week, not the staging loop. Server error is undefined, there is no baseline or control, and the post also credits thousands of editor fixes in the same weeks.
- [1] Rust was a hypothesis, not a bake-off.
- [2] Fixes shipped behind runtime flags.
- [3] One run on an internal research model; no drift rate.
- [4] The $3,000 to $10,000 small-stack figure is an unrun estimate.

Dive record: 2026-11-24 Stage-2 wave 1 (dive B, sonnet, FULL): 5 claims, 3 CONFIRMED, 2 PARTIAL. The headline is uncontrolled and the model internal. Live-lesson tests: L1 adds context (no resume mechanism; it relied on one persistent coordinator session); L2 silent (dedicated staging cluster, no shared-host contention). The up-front approval list for irreversible decisions is already our Act-Don't-Defer admission test.

Contradicting or limiting evidence:

- No control separates the loop's effect from the editor fixes credited in the same weeks; internal research model, not reproducible with public models.

