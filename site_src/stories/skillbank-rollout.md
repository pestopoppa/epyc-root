# SkillBank: turning trajectories into skills

The orchestrator has been recording every routing decision into an episodic memory store since the MemRL system came online. Each entry is a trajectory: task in, route taken, model invoked, outcome, latency, quality signal if available. By mid-2026 the store had grown past 2,700 entries and a clear problem had emerged. The store was big enough that retrieval-at-inference time was working — the FAISS index lookup that powers the learned router could find the closest few past episodes per request — but raw trajectories make awful prompt context. They're long, noisy, and contain a lot of detail that doesn't generalize.

SkillBank is the answer to that problem. It's a layer on top of the episodic store that distills raw trajectories into structured, reusable "skills" — short behavioural principles that encode what the trajectory taught us, optimized for prompt injection rather than for replay.

## What the original paper claimed and what it implied for us

SkillRL (the underlying research) ran an ablation: replace structured skills with raw trajectories in their agent and watch performance drop. The numbers were striking — −28.2 % on ALFWorld, −22.5 % on WebShop. The same paper showed that a 7 B model with skill augmentation hit 89.9 % on ALFWorld, ahead of GPT-4o's 48 % and Gemini-2.5-Pro's 60.3 %. The implication for our stack was direct: a substantial part of the gap between our worker tier and the architect tier might close not by enlarging the worker, but by giving the worker access to architect-derived skills.

That's a load-bearing claim. If it holds, the project's escalation chain becomes more about *bridging* model tiers than about *replacing* small models with large ones — the worker stays at 26 B but punches above its weight on tasks where it has an applicable skill in context.

## The architecture

SkillBank is a materialized view over the episodic store. Raw trajectories stay intact for Q-learning, replay evaluation, and audit. Skills are derived, lossy, optimized for inference. The distinction matters because it lets us iterate on the distillation pipeline without losing source material.

The flow has four stations. A periodic batch job runs the distiller over recent episodic-store entries, with one of three teacher models doing the actual distillation — Claude Opus 4.6 for high-quality production runs, Codex GPT-5.3 for code-heavy trajectories, or the local Qwen3-235B for cheap bulk passes. The output is a `Skill` record with a behavioural principle, a context-discriminator field, provenance links back to the source trajectories, and effectiveness-tracking fields that get updated over time. Skills live in their own SQLite database with a companion FAISS vector index, capped at 500 entries to keep the index small enough for sub-ms lookup.

At inference time the SkillRetriever pulls relevant skills (typically the top 2-3 by embedding similarity to the current task) and injects them into the prompt before the model sees the task. The retriever is wrapped around the existing HybridRouter, so it's strictly additive — if no skills clear the relevance threshold, nothing gets injected and the request flows through unchanged.

The fourth station is the ReplayEngine, which works offline. It can take an existing trajectory from the episodic store, re-run it under different routing or skill configurations, and measure how the outcome would have changed. That gives us a way to evaluate skill effectiveness without spending production traffic on it.

## The token economics

The whole bet rests on the token-economics math. A typical raw trajectory in the episodic store is 1,000-4,000 tokens depending on task complexity. A typical distilled skill is 80-150 tokens. So a 20× compression is the conservative case; high-noise trajectories compress closer to 30×. For a prompt budget of 4-6 retrieved memories per request, the choice is between injecting ~12,000 tokens of raw trajectory context or ~500 tokens of structured skills.

For a CPU stack where every token of prompt context costs measurable bandwidth, the compression is operationally significant. The router can effectively look back farther — across more historical episodes — at the same per-request token budget.

## Where it sits in production

SkillBank is fully implemented as of 2026-05. The code is in the orchestrator repo (`src/skillbank/`, `src/graph/skill_retriever.py`). The SQLite + FAISS storage works. The distillation pipeline runs nightly during AutoPilot's off-hours. The retriever is wrapped around the HybridRouter.

It is **not yet enabled in production**. The feature flag (`skillbank.enabled`) defaults to `false` while we collect the full-scale distillation pass — currently about 180 distilled skills from ~700 source trajectories, which is below the ~500 mark where the FAISS index will pay off the lookup cost on every request. A/B testing is queued behind that data-collection run.

The decision to ship feature-flagged-off is deliberate. The cost of having SkillBank latently in the codebase is small; the cost of enabling it in shadow mode and discovering a retrieval-side regression mid-week is large. Once the distillation pass clears 500 skills and the retriever has a critical mass of high-quality candidates, the A/B test flips on and we measure against the orchestrator without skill augmentation. Expected outcome based on the SkillRL ablation: workers (gemma-4-26B-A4B) should claw back 10-15 % of the worker-to-architect gap on tool-call-heavy tasks. We'll know.

## What this story is really about

The SkillBank rollout is an instance of a broader pattern that recurs in the project: **the highest-leverage feature in the routing layer often isn't a better model or a smarter rule, it's a better representation of what you already know**. We had 2,700 episodes in the store and a learned classifier that knew which model to call. The classifier didn't yet know what *kind of help* to bring with each call. SkillBank closes that gap.

The deeper implication is that as the episodic store grows past some threshold (we're seeing the threshold around 1,000 entries), the orchestrator stops being primarily a routing system and starts being primarily a *memory* system. Routing is a one-shot decision; memory is the substrate that lets routing be smart. The next round of work — once the A/B test lands — is about how the skills feed back into the routing classifier itself, so the classifier's score for a route accounts for whether good skills are available to inject. That's the loop we want to close in Q3 2026.

For deeper reading, [SkillBank & Experience Distillation](../subsystems/orchestrator/15-skillbank-experience-distillation.md) is the in-repo chapter, and [MemRL System](../subsystems/orchestrator/07-memrl-system.md) is the broader memory-substrate story this builds on. The autonomous-research loop that generated the SkillRL paper into a deep-dive into an architecture sketch into deployed code is described in [The autonomous research loop](autonomous-research-loop.md).
