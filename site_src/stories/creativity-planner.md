# The constrained-creativity planner upgrade

AutoPilot's planner has to do a peculiar thing on each trial: it has to *propose the next experiment*. It has the journal of past trials, the current Pareto frontier, and an LLM (the controller, usually the architect tier) that's been given all of that context plus a prompt template. The output is supposed to be a config change worth testing.

For the first few months of AutoPilot's operation, this worked the obvious way. The planner kept a list of action types (model swaps, quantization changes, NUMA layout tweaks, KV-compression settings, …) and the controller picked one each trial. When the planner wanted to encourage exploration — to push out of a local Pareto-frontier ridge — it would shuffle in "tail" candidates: action types that had appeared at most once in the last 30 trials, presented as equal-footing alternatives to the obvious answer.

That mechanism was net-positive but worked less well than it should have. The 2026-05-23 upgrade was a focused intervention to make it actually function as designed.

## Three failure modes the original mechanism had

The audit identified three structural problems:

**Tail candidates competed on equal footing with the obvious answer.** When the controller saw three off-default actions presented alongside the modal one, the response was usually a paragraph or two of reasoning that landed on the modal action anyway. The off-defaults functioned as performative diversity — they were in the prompt but they didn't change the output. There was no rubric grounding the comparison, so the controller's "I considered alternatives" reasoning was costless and the alternatives were dismissed in a sentence each.

**The mechanism ran every trial.** Including exploit-phase trials on a working lead. The controller spent prompt budget enumerating tail candidates even when the current frontier was actively improving and the right move was to push harder along the same axis. Wasted tokens, and worse, the wasted tokens trained the controller to treat the diversity-enumeration as a perfunctory step.

**No falsifier was recorded.** When an off-default action *was* chosen, the controller would have offered some implicit reasoning for why it should work — but the reasoning evaporated as soon as the trial finished. The next planner pass saw the outcome (success or failure) but not the *prediction it was supposed to invalidate*. The signal value of a successful off-default trial collapsed to "this action sometimes works" rather than "this action validates hypothesis X about the configuration space."

Each of these is a soft failure: not a bug, not a regression, but a mechanism that's working at maybe 30 % of its design potential.

## The synthesis the deep-dive landed on

The deep-dive that drove the upgrade (`research/deep-dives/2026-05-23-creativity-constrained-tail-search.md`) develops a model of creative search based on three claims, each with a concrete operational implication:

| Claim | What it implies for the planner |
|---|---|
| Novelty alone is not creativity — the raw tail is mostly garbage | Generate under truth-preserving constraints, not just by raising temperature |
| Creative ideas live on a ridge of high novelty × high validity × high compression | Score candidates on three orthogonal axes (info gain, coherence, cost-adjusted usefulness), not six adjacent ones |
| Real insight lowers entropy *out-of-sample* — delusion only on data already seen | Persist a falsifier with every chosen action; surface still-open ones to the next pass |

The framing matters because the upgrade isn't just better mechanics — it's a different theory of what the creative step is *for*. The previous mechanism treated creativity as exploration of a probability distribution over actions. The new mechanism treats it as constrained generation of falsifiable hypotheses about the configuration space. These have very different implementation profiles.

## Four moves that landed

The actual implementation is small. Four concrete changes replaced the prior tail-shuffle mechanism, all in one session:

The first was promoting tail samples from candidates to seeds. Under-used action types are now surfaced as inspiration ("directions explored ≤1 time in last 30 trials") rather than mandatory candidates. The controller isn't asked to argue *against* them; the framing is "here are some lines of attack that haven't been tried recently." Diversity priming without forcing the model to debate noise.

The second was stagnation gating. The rich creativity protocol activates only when one of three signals fires: hypervolume slope below `STAGNATION_HV_EPS = 1e-3`, trustworthy trial count below 5, or three consecutive trials with the same `action_type`. Otherwise the planner uses a lean prompt that skips the creativity machinery. Structured creativity has a cost; pay it only when stuck.

The third was collapsing the rubric from six axes to three. The original rubric had axes like "novelty," "feasibility," "expected gain," "alignment with frontier," and two others. They overlapped semantically and the controller would mush its scores across them. Three orthogonal axes — information gain (novelty + falsifiability + compression), coherence with evidence, and cost-adjusted usefulness — turn out to be the sweet spot. LLMs grade more crisply across three orthogonal axes than six adjacent ones.

The fourth was persisting the falsifier. A second fenced block (`autopilot_rationale`) now carries the chosen action's falsifier and self-scored rubric. Both fields land on `JournalEntry` as new optional fields with `.get(field, default)` migration. A new `ExperimentJournal.unfalsified_hypotheses()` helper surfaces still-open claims to the next planner pass, so the next controller sees "here are three predictions from past trials that haven't been resolved yet" alongside the current task.

Two further refinements ride along. **Fusion preference**: if the top-two candidates can be encoded as one action that dominates both, the planner is biased to prefer the fusion. This is a small anti-fragmentation prior. And **quote-don't-regenerate**: the chosen action's rubric scores must be copied verbatim from the candidate table rather than re-derived in the rationale. That's an anti-drift guard against the performative-reasoning failure mode — if you have to quote the scores, you can't quietly raise them while writing the rationale.

## The failure modes still latent

None of the four guards is bulletproof. The deep-dive catalogues the failure modes that remain:

| Failure mode | What guards against it now |
|---|---|
| Performative reasoning (controller writes a rubric, picks the modal answer) | Quote-don't-regenerate rule on the rationale sidecar |
| Rubric drift / score mushing across adjacent axes | Three orthogonal axes (collapsed from six) |
| Falsifier inflation (vague non-answers) | Persistence to journal + surfacing still-open ones; useless falsifiers age out |
| Local-optimum defence (alternatives dismissed in a sentence) | Stagnation gate + fresh tail seeds each pass |

None of these is fully eliminated. The intent isn't elimination — it's *raising the cost of the failure mode enough that the cheaper path is to do the right thing*. Performative reasoning is still possible; it's now more work than just doing the genuine analysis. That's the whole game.

## What this story is really about

This is a small upgrade — about 200 lines of Python across three files, plus tests. But it's a clean example of the project's recurring pattern: **most agent improvements come from changing what the agent is allowed to fail at**, not from making it smarter. The old mechanism let the controller fail at "diversity-enumeration" in a way that looked successful. The new mechanism makes that failure visible (no falsifier persisted, or rubric scores that contradict the choice) and therefore correctable.

The other thread worth pulling on is the role of the **research deep-dive that preceded the implementation**. The synthesis framework, the failure-mode catalogue, the three-axes rubric — all of these came from a single research document written before any code changed. The implementation session converted that document into deployed mechanics in a few hours. That's the autonomous-research loop in microcosm: a paper-shaped artifact (a deep-dive) translated into production behavior with the deep-dive serving as the implementation spec. [The autonomous research loop](autonomous-research-loop.md) is the broader version of this pattern.

For further reading, [LLM Prompting](../topics/llm-prompting.md) covers the prompt-design patterns this upgrade draws on, and [Autonomous Research](../topics/autonomous-research.md) is the topic synthesis that includes the constrained-creativity finding alongside related autopilot work.
