# Dive C-permissions-deferral (intake run always-on-1124, 2026-11-24)

Stage-2 deep dive. Sources were read from the retained anchor snapshots through the machine_anchor extractor; every anchored quote is an exact substring of that text and carries a script-written anchor_mark in the index. In-house reads at epyc-root 3b11e6c82 (no drift to a290df6 on the cited files) and epyc-inference-research 82d5822.

## intake-2947: How we built Claude Code auto mode: a safer way to skip permissions (John Hughes, Anthropic, 2026-03-25)

- URL: https://www.anthropic.com/research/claude-code-auto-mode
- Read depth: FULL
- Verdict: worth_investigating; relevance medium; credibility 3

| # | Claim | Status | Locator |
|---|---|---|---|
| 0 | The full two-stage pipeline has a 0.4% false-positive rate on 10,000 real internal tool calls. | CONFIRMED | Results |
| 1 | Recall is weaker than the headline: 17% false negatives on real overeager actions (n=52), which the post calls the honest number. | PARTIAL | Results |
| 2 | A block returns to the agent with its reason so it tries a safer path; 3 consecutive or 20 total denials stop the model and escalate, and headless mode terminates. | CONFIRMED | Design decisions (Deny-and-continue) |
| 3 | The classifier strips assistant text and tool results so the agent cannot argue it into a bad call. | CONFIRMED | Design decisions (Why we strip assistant text and tool results) |
| 4 | Evaluation was offline on three datasets; no staged, shadow or warn-first rollout of the classifier is described. | NOT-FOUND-IN-SOURCE | Results |

Claim notes:

- [0] Stage 1 alone is 8.5% FPR. Anthropic-internal traffic only.
- [1] Narrowed: catches most, not all; n=52 is small; misses are mostly consent-scope errors.
- [2] A false positive costs one retry.
- [3] Including them lowered performance; no figure given.
- [4] The post describes datasets, not a rollout path.

Dive record: 2026-11-24 Stage-2 wave 1 (dive C, sonnet, FULL): 5 claims, 3 CONFIRMED, 1 PARTIAL, 1 NOT-FOUND-IN-SOURCE (no warn-first or shadow rollout of the classifier). Live-lesson tests: L1 adds (a refusal is a retry signal bounded by a counter: 3 consecutive or 20 total, then escalate; the Codex lane cx10 treated a refused light claim as a stop and was resumed by a hand-written continue message with no counter); L4 neither supports nor contradicts (offline FPR/FNR before trusting a gate is the measurement analogue of PM-RULES-WARN-FIRST's would-fail count); L5 agrees (judge what the agent did, not what it says).

Contradicting or limiting evidence:

- 17% FNR on real overeager actions, which the post says is arguably a regression against careful manual approval; no independent replication.

## intake-2948: Claude Code hooks reference: deferred tool calls and async rewake (docs, read 2026-11-24)

- URL: https://code.claude.com/docs/en/hooks
- Read depth: PARTIAL
- Verdict: adopt_patterns; relevance high; credibility None

| # | Claim | Status | Locator |
|---|---|---|---|
| 0 | A defer decision ends the turn with stop_reason tool_deferred and keeps the pending call in the transcript; the caller resumes with claude -p --resume and the hook fires again. | CONFIRMED | Defer a tool call for later |
| 1 | An asyncRewake hook that exits 2 wakes an idle session and shows its stderr as a system reminder. | CONFIRMED | Run hooks in the background |
| 2 | Async hooks cannot block; blocking needs a synchronous hook with exit 2 or a deny decision. | PARTIAL | Run hooks in the background |

Claim notes:

- [0] Headless -p only, single tool call per turn, no timeout; session kept until cleanupPeriodDays (30 days default); permission mode is not restored on resume.
- [1] Matches our own WS-4 spike GO of 2026-11-19.
- [2] The Stop-hook decision-control body was not read.

Dive record: 2026-11-24 Stage-2 wave 1 (dive C, sonnet, PARTIAL: read the defer section, the async and asyncRewake paragraphs, the PreToolUse decision table and the SubagentStop input; not read: the Stop, TeammateIdle and TaskCompleted decision bodies, other events, prompt/agent/http hook types and the bundled JS). 3 claims, 2 CONFIRMED, 1 PARTIAL. Live-lesson test: L1 adds a documented suspend-and-resume path for claude -p actors. It does not apply to taskflow workers (opencode on local models) or Codex lanes, and no deferred-call-to-inbox-to-resume path exists in taskflow dispatch.py.

Contradicting or limiting evidence:

- Defer is unavailable interactively and for parallel tool calls, and resume does not restore the permission mode.

## intake-2949: Building effective agent automations (Lance Martin and CJ Avilla, Anthropic, 2026-10-08)

- URL: https://claude.dev/blog/building-effective-agent-automations/
- Read depth: FULL
- Verdict: adopt_patterns; relevance medium; credibility 2

| # | Claim | Status | Locator |
|---|---|---|---|
| 0 | A per-source bookmark replaces fixed time windows. | CONFIRMED | Sources (Read from where you left off) |
| 1 | A down source looks like an empty one, so the agent must name what it could not read instead of reporting nothing new. | CONFIRMED | Sources (Don't mistake a failed read for a quiet day) |
| 2 | A post counts as sent only on explicit confirmation from the destination, and the ledger updates only after that. | CONFIRMED | Destination (Confirm the post landed before recording it) |
| 3 | If the preferences store cannot be read the run stops rather than using defaults; a run that hits its budget pauses with a budget_reached reason. | CONFIRMED | Memory and Guardrails |

Claim notes:

- [0] Knowledge-only for us.
- [1] Same class as our fail-open and vacuous-verification lessons.
- [2] An unclear result is recorded as maybe posted with nothing else changed.
- [3] No measurements anywhere in the post.

Dive record: 2026-11-24 Stage-2 wave 1 (dive C, sonnet, FULL): 4 claims, all CONFIRMED. Live-lesson test: L5 agrees (completion judged from an external artifact, ledger updated afterwards; taskflow verify.py already works this way, and the maybe-posted state matches its unchecked verdict). The write-ahead record is a design note for PM-PUBLISH-REHEARSAL. Dive-surfaced source: anthropic.com/research/managed-agents is already indexed as intake-2616; cross-reference only.

Contradicting or limiting evidence:

- Each run is a fresh session by design, so it has no resume of an interrupted run.

