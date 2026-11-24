# Dive E-agent-time (intake run always-on-1124, 2026-11-24)

Stage-2 deep dive. Sources were read from the retained anchor snapshots through the machine_anchor extractor; every anchored quote is an exact substring of that text and carries a script-written anchor_mark in the index. In-house reads at epyc-root 3b11e6c82 (no drift to a290df6 on the cited files) and epyc-inference-research 82d5822.

## intake-2953: AgentTime: Can Agents Estimate and Control Their Own Runtime?

- URL: https://arxiv.org/abs/2610.09944v2
- Read depth: PARTIAL
- Verdict: worth_investigating; relevance high; credibility 3

| # | Claim | Status | Locator |
|---|---|---|---|
| 0 | Asked to work for a requested duration, GPT-6 Astra in Codex ends 63% of runs within 5% of it, GPT-5.6 Sol 39% and Fable 5.1 in Claude Code 4%. | PARTIAL | 4.1 Duration-Following |
| 1 | With an elapsed-time tool, agents' retrospective estimates of time spent are almost exact. | CONFIRMED | 4.3 Estimating Time Spent |
| 2 | Agents' forecasts of their own natural runtime are mostly too high. | CONFIRMED | 4.2 Forecasting Natural Runtimes |
| 3 | Fable 5.1 returns early on 55% of runs and on 89% of the longest requests, at a median of 0.3 of the requested time. | CONFIRMED | 4.1 Duration-Following |
| 4 | The controller never resumes or coaches an agent that returns early. | CONFIRMED | 4.1 Setup |
| 5 | Being on time is not the same as working: most on-time Astra runs re-checked or slept after appearing to finish. | CONFIRMED | 4.1 Being on time is not the same as working |
| 6 | More requested time rarely changes the score, with occasional exceptions. | PARTIAL | 4.1 More time rarely changes the score |

Claim notes:

- [0] Numbers confirmed, but the metric is following a user-requested duration (1.25 min to 60 h), not unprompted stopping; a harness swap shows the gap is mostly the model.
- [1] Misses of 2 to 5 times appear only when time cues are stripped.
- [2] Median forecast 15 min versus natural medians of 6, 10 and 13 min.
- [3] Sol returns early 13% and Astra 3%; Table 3.
- [4] So the paper has no data on whether a resume loop fixes early exit.
- [5] 11 of 49 on-time agentic Astra runs met the working rule.
- [6] One anecdote; scores were unchanged for 62 to 64% of tasks.

Dive record: 2026-11-24 Stage-2b wave 2 (dive E, sonnet, PARTIAL: body sections 1-7 read in full from the arXiv v2 HTML; not read: second half of Appendix B, Appendices C-F, references). 7 claims, 5 CONFIRMED, 2 PARTIAL. It settles intake-2950 claim 2: the figures are exact but describe duration-following, and Astra plus the oracle tool contradict 'models are poor clocks'. Live-lesson tests: L1 agrees that early return is common and model-dependent without a resume loop (Fable returns early 55%), and the paper never resumes, so it gives no evidence on the fix; L5 adds that self-declared completion and elapsed time are both unreliable signals. Dive-surfaced sources declined at the two-wave cap: arXiv 2604.00010, github.com/michaelofengenden/agenttimebench, arXiv 2601.16486, arXiv 2606.00198.

Contradicting or limiting evidence:

- One run per task per duration with no repeats (stated by the authors); three agents from two labs.
- Astra's 63% on time and the oracle-tool result contradict the blanket reading that models are poor clocks (intake-2950).

## intake-2954: Your LLM Agents are Temporally Blind: The Misalignment Between Tool Use Decisions and Human Time Perception

- URL: https://arxiv.org/abs/2510.23853v3
- Read depth: PARTIAL
- Verdict: worth_investigating; relevance low; credibility 3

| # | Claim | Status | Locator |
|---|---|---|---|
| 0 | TicToc tests whether agents refresh stale context with a tool call or answer directly, over 3016 retained preference samples. | CONFIRMED | 3.5 Preference collection and aggregation |
| 1 | With timestamps in context no model exceeds a 65% normalized alignment rate; without them models are near chance. | CONFIRMED | Abstract and 4.1 |
| 2 | A generic time-awareness reminder had little to no effect; DPO on open models up to 8B helped. | PARTIAL | 4.4 Alignment efforts |

Claim notes:

- [0] Narrower than the title: refresh decisions, not runtime or stopping.
- [1] NAR is balanced accuracy, 50% is chance.
- [2] The DPO gains are only in figures; the test set is held-out scenarios from the same synthetic distribution.

Dive record: 2026-11-24 Stage-2b wave 2 (dive E, sonnet, PARTIAL: body sections 1-5 read; appendices A-D and references not read). 3 claims, 2 CONFIRMED, 1 PARTIAL. Low relevance: it concerns stale-context refresh decisions, which no EPYC agent makes from elapsed time (scheduling is deterministic in taskflow dispatch.py and the session bus). No actionable.

Contradicting or limiting evidence:

- Trajectories and timestamps are synthetic (GPT-4o generated, GPT-4.1 filtered) and labels are hypothetical human preferences, not task success.

