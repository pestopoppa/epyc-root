# Hermes Agent — Integration Index

**Status**: active
**Created**: 2026-03-15 (split from hermes-agent-index.md on 2026-03-20)
**Source**: intake-117 (hermes-agent), intake-172/173 (OpenGauss fork)

## Background

Hermes Agent (Nous Research) is an open-source autonomous AI agent with persistent memory, self-improving skills, and user modeling. OpenGauss (Math, Inc.) is a production fork specialized for Lean 4 theorem proving — 170 stars in 1 day, proving the architecture works for vertical domains.

Key findings from analysis (2026-03-15) and deep dive (2026-03-20):

- Memory system: 2 bounded flat files + FTS5 cross-session search + context compression via auxiliary LLM
- Skill system: mature (agentskills.io standard, hub aggregating 7 sources, security scanning pipeline)
- User modeling: Honcho (Plastic Labs) — dialectic LLM-to-LLM reasoning about user preferences
- Fully model-agnostic — works with any OpenAI-compatible endpoint via `base_url`
- OpenGauss adds: multi-backend abstraction (Claude Code + Codex), ACP server, swarm coordination, session analytics

## Integration Paths

These are **independent, non-competing** workstreams that can proceed in parallel:

### Path A — User-Facing Agent Shell

**Handoff**: [`hermes-outer-shell.md`](hermes-outer-shell.md)

Layer Hermes/OpenGauss on top of our orchestrator as a user-facing frontend. It handles conversation UX, memory, skills, multi-platform gateway. Our orchestrator handles routing, model selection, inference optimization underneath.

**When**: After core orchestrator features stabilize. Low urgency.

### Path B — Cherry-Pick Patterns into Orchestrator

**Handoff**: [`orchestrator-conversation-management.md`](orchestrator-conversation-management.md)

Port the best implementation patterns from Hermes/OpenGauss directly into our orchestrator: context compression, user modeling, session analytics, multi-backend abstraction.

**When**: B1 (user modeling) and B2 (context compression) are high value now. Others can wait.

## Research Context

| Intake ID | Title | Relevance |
|-----------|-------|-----------|
| intake-117 | Hermes Agent | Original discovery |
| intake-144 | Deep Agents | Architectural parallel (LangGraph) |
| intake-145 | Agent Protocol | API standard (Runs/Threads/Store) |
| intake-171 | FormalQualBench | Agent harness benchmark |
| intake-172 | OpenGauss (blog) | Production hermes-agent fork |
| intake-173 | OpenGauss (repo) | Implementation details |

## Deep Dives

- `research/deep-dives/opengauss-architecture-analysis.md` — 10 architectural patterns identified
- `research/deep-dives/langgraph-ecosystem-comparison.md` — Agent Protocol naming alignment
